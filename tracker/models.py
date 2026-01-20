import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


def _generate_unique_value(*, model_cls: type[models.Model], field_name: str, generator) -> str:
	for _ in range(50):
		value = generator()
		if value and not model_cls.objects.filter(**{field_name: value}).exists():
			return value
	raise RuntimeError(f"Unable to generate unique {model_cls.__name__}.{field_name}")


class Clinic(models.Model):
	name = models.CharField(max_length=255)
	clinic_code = models.CharField(max_length=32, unique=True, editable=False)
	created_at = models.DateTimeField(auto_now_add=True)

	def save(self, *args, **kwargs):
		if not self.clinic_code:
			self.clinic_code = _generate_unique_value(
				model_cls=Clinic,
				field_name='clinic_code',
				generator=lambda: secrets.token_hex(4),
			)
		return super().save(*args, **kwargs)

	def __str__(self) -> str:
		return f"{self.name} ({self.clinic_code})"


class UserProfile(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	clinic = models.ForeignKey(Clinic, on_delete=models.PROTECT)

	def __str__(self) -> str:
		return f"{self.user.username} -> {self.clinic}"


class FollowUp(models.Model):
	class Language(models.TextChoices):
		EN = 'en', 'English'
		HI = 'hi', 'Hindi'

	class Status(models.TextChoices):
		PENDING = 'pending', 'Pending'
		DONE = 'done', 'Done'

	clinic = models.ForeignKey(Clinic, on_delete=models.PROTECT, related_name='followups')
	created_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.PROTECT,
		related_name='created_followups',
	)
	patient_name = models.CharField(max_length=255)
	phone = models.CharField(max_length=32)
	language = models.CharField(max_length=2, choices=Language.choices, default=Language.EN)
	notes = models.TextField(blank=True)
	due_date = models.DateField()
	status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
	public_token = models.CharField(max_length=64, unique=True, editable=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def save(self, *args, **kwargs):
		if not self.public_token:
			self.public_token = _generate_unique_value(
				model_cls=FollowUp,
				field_name='public_token',
				generator=lambda: secrets.token_urlsafe(18)[:32],
			)
		return super().save(*args, **kwargs)

	@property
	def is_overdue(self) -> bool:
		return self.due_date < timezone.localdate()

	def __str__(self) -> str:
		return f"{self.patient_name} ({self.phone}) - {self.status}"


class PublicViewLog(models.Model):
	followup = models.ForeignKey(FollowUp, on_delete=models.CASCADE, related_name='public_view_logs')
	viewed_at = models.DateTimeField(auto_now_add=True)
	user_agent = models.CharField(max_length=255, blank=True)
	ip_address = models.CharField(max_length=64, blank=True)

	def __str__(self) -> str:
		return f"{self.followup_id} @ {self.viewed_at.isoformat()}"
