from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Clinic, FollowUp, PublicViewLog, UserProfile


class TrackerTests(TestCase):
	def setUp(self):
		User = get_user_model()

		self.clinic1 = Clinic.objects.create(name='Clinic One')
		self.clinic2 = Clinic.objects.create(name='Clinic Two')

		self.user1 = User.objects.create_user(username='u1', password='pass12345')
		self.user2 = User.objects.create_user(username='u2', password='pass12345')

		UserProfile.objects.create(user=self.user1, clinic=self.clinic1)
		UserProfile.objects.create(user=self.user2, clinic=self.clinic2)

		self.followup1 = FollowUp.objects.create(
			clinic=self.clinic1,
			created_by=self.user1,
			patient_name='Patient A',
			phone='+15551234567',
			language=FollowUp.Language.EN,
			notes='Test',
			due_date=date.today() + timedelta(days=3),
			status=FollowUp.Status.PENDING,
		)

	def test_unique_clinic_code_generation(self):
		self.assertTrue(self.clinic1.clinic_code)
		self.assertTrue(self.clinic2.clinic_code)
		self.assertNotEqual(self.clinic1.clinic_code, self.clinic2.clinic_code)

	def test_unique_public_token_generation(self):
		followup2 = FollowUp.objects.create(
			clinic=self.clinic1,
			created_by=self.user1,
			patient_name='Patient B',
			phone='+15550001111',
			language=FollowUp.Language.EN,
			due_date=date.today() + timedelta(days=4),
			status=FollowUp.Status.PENDING,
		)
		self.assertTrue(self.followup1.public_token)
		self.assertTrue(followup2.public_token)
		self.assertNotEqual(self.followup1.public_token, followup2.public_token)

	def test_dashboard_requires_login(self):
		resp = self.client.get(reverse('dashboard'))
		self.assertEqual(resp.status_code, 302)
		self.assertIn('/accounts/login/', resp['Location'])

	def test_cross_clinic_access_blocked(self):
		self.client.login(username='u2', password='pass12345')
		resp = self.client.get(reverse('followup_edit', kwargs={'pk': self.followup1.pk}))
		self.assertEqual(resp.status_code, 404)

	def test_public_page_creates_view_log(self):
		self.assertEqual(PublicViewLog.objects.count(), 0)
		resp = self.client.get(reverse('public_followup', kwargs={'public_token': self.followup1.public_token}))
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(PublicViewLog.objects.count(), 1)
		log = PublicViewLog.objects.first()
		self.assertEqual(log.followup_id, self.followup1.id)

	def test_mark_done_is_post_only_and_updates_status(self):
		self.client.login(username='u1', password='pass12345')
		url = reverse('followup_mark_done', kwargs={'pk': self.followup1.pk})

		get_resp = self.client.get(url)
		self.assertEqual(get_resp.status_code, 405)

		post_resp = self.client.post(url)
		self.assertEqual(post_resp.status_code, 302)
		self.followup1.refresh_from_db()
		self.assertEqual(self.followup1.status, FollowUp.Status.DONE)

	def test_export_csv_is_clinic_scoped(self):
		FollowUp.objects.create(
			clinic=self.clinic2,
			created_by=self.user2,
			patient_name='Other Clinic Patient',
			phone='+15559990000',
			language=FollowUp.Language.EN,
			due_date=date.today() + timedelta(days=7),
			status=FollowUp.Status.PENDING,
		)

		self.client.login(username='u1', password='pass12345')
		resp = self.client.get(reverse('followups_export_csv'))
		self.assertEqual(resp.status_code, 200)
		self.assertIn('text/csv', resp['Content-Type'])
		content = resp.content.decode('utf-8')
		self.assertIn(self.followup1.patient_name, content)
		self.assertNotIn('Other Clinic Patient', content)

	def test_dashboard_pagination_second_page(self):
		for i in range(30):
			FollowUp.objects.create(
				clinic=self.clinic1,
				created_by=self.user1,
				patient_name=f'P{i}',
				phone='+15550001234',
				language=FollowUp.Language.EN,
				due_date=date.today() + timedelta(days=10 + i),
				status=FollowUp.Status.PENDING,
			)

		self.client.login(username='u1', password='pass12345')
		resp = self.client.get(reverse('dashboard') + '?page=2')
		self.assertEqual(resp.status_code, 200)
		self.assertIn('Page 2', resp.content.decode('utf-8'))
