from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date

from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import FollowUpForm
from .models import FollowUp, PublicViewLog, UserProfile


@dataclass(frozen=True)
class ClinicContext:
	clinic_id: int


def _get_user_clinic_context(request: HttpRequest) -> ClinicContext:
	try:
		profile: UserProfile = request.user.userprofile  # type: ignore[attr-defined]
	except Exception as exc:
		raise Http404('User profile/clinic not configured') from exc
	return ClinicContext(clinic_id=profile.clinic_id)


def _client_ip(request: HttpRequest) -> str:
	xff = (request.META.get('HTTP_X_FORWARDED_FOR') or '').split(',')[0].strip()
	if xff:
		return xff[:64]
	return (request.META.get('REMOTE_ADDR') or '')[:64]


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
	clinic_ctx = _get_user_clinic_context(request)

	base_qs = (
		FollowUp.objects.filter(clinic_id=clinic_ctx.clinic_id)
		.select_related('clinic', 'created_by')
		.annotate(view_count=Count('public_view_logs', distinct=True))
		.order_by('due_date', '-created_at')
	)

	status = (request.GET.get('status') or '').strip()
	due_start = (request.GET.get('due_start') or '').strip()
	due_end = (request.GET.get('due_end') or '').strip()

	filtered_qs = base_qs
	if status in {FollowUp.Status.PENDING, FollowUp.Status.DONE}:
		filtered_qs = filtered_qs.filter(status=status)

	date_filters = Q()
	if due_start:
		try:
			date_filters &= Q(due_date__gte=date.fromisoformat(due_start))
		except ValueError:
			pass
	if due_end:
		try:
			date_filters &= Q(due_date__lte=date.fromisoformat(due_end))
		except ValueError:
			pass
	if date_filters:
		filtered_qs = filtered_qs.filter(date_filters)

	summary_qs = FollowUp.objects.filter(clinic_id=clinic_ctx.clinic_id)
	summary = {
		'total': summary_qs.count(),
		'pending': summary_qs.filter(status=FollowUp.Status.PENDING).count(),
		'done': summary_qs.filter(status=FollowUp.Status.DONE).count(),
	}

	try:
		page_number = int(request.GET.get('page') or '1')
	except ValueError:
		page_number = 1

	per_page = 25
	paginator = Paginator(filtered_qs, per_page)
	page_obj = paginator.get_page(page_number)

	qs_no_page = request.GET.copy()
	qs_no_page.pop('page', None)
	qs_no_page_str = qs_no_page.urlencode()

	return render(
		request,
		'tracker/dashboard.html',
		{
			'followups': page_obj,
			'page_obj': page_obj,
			'qs_no_page': qs_no_page_str,
			'summary': summary,
			'filters': {'status': status, 'due_start': due_start, 'due_end': due_end},
		},
	)


@login_required
def followups_export_csv(request: HttpRequest) -> HttpResponse:
	clinic_ctx = _get_user_clinic_context(request)

	base_qs = (
		FollowUp.objects.filter(clinic_id=clinic_ctx.clinic_id)
		.annotate(view_count=Count('public_view_logs', distinct=True))
		.order_by('due_date', '-created_at')
	)

	status = (request.GET.get('status') or '').strip()
	due_start = (request.GET.get('due_start') or '').strip()
	due_end = (request.GET.get('due_end') or '').strip()

	filtered_qs = base_qs
	if status in {FollowUp.Status.PENDING, FollowUp.Status.DONE}:
		filtered_qs = filtered_qs.filter(status=status)

	date_filters = Q()
	if due_start:
		try:
			date_filters &= Q(due_date__gte=date.fromisoformat(due_start))
		except ValueError:
			pass
	if due_end:
		try:
			date_filters &= Q(due_date__lte=date.fromisoformat(due_end))
		except ValueError:
			pass
	if date_filters:
		filtered_qs = filtered_qs.filter(date_filters)

	timestamp = timezone.localtime().strftime('%Y%m%d-%H%M%S')
	filename = f'followups-{timestamp}.csv'

	response = HttpResponse(content_type='text/csv; charset=utf-8')
	response['Content-Disposition'] = f'attachment; filename="{filename}"'

	writer = csv.writer(response)
	writer.writerow(
		[
			'patient_name',
			'phone',
			'language',
			'due_date',
			'status',
			'notes',
			'public_token',
			'view_count',
			'created_at',
			'updated_at',
		]
	)
	for followup in filtered_qs:
		writer.writerow(
			[
				followup.patient_name,
				followup.phone,
				followup.language,
				followup.due_date.isoformat(),
				followup.status,
				followup.notes,
				followup.public_token,
				getattr(followup, 'view_count', 0),
				followup.created_at.isoformat() if followup.created_at else '',
				followup.updated_at.isoformat() if followup.updated_at else '',
			]
		)

	return response


@login_required
def followup_create(request: HttpRequest) -> HttpResponse:
	clinic_ctx = _get_user_clinic_context(request)
	if request.method == 'POST':
		form = FollowUpForm(request.POST)
		if form.is_valid():
			followup: FollowUp = form.save(commit=False)
			followup.clinic_id = clinic_ctx.clinic_id
			followup.created_by = request.user
			followup.save()
			messages.success(request, 'Follow-up created.')
			return redirect('dashboard')
	else:
		form = FollowUpForm()

	return render(request, 'tracker/followup_form.html', {'form': form, 'mode': 'create'})


@login_required
def followup_edit(request: HttpRequest, pk: int) -> HttpResponse:
	clinic_ctx = _get_user_clinic_context(request)
	followup = get_object_or_404(FollowUp, pk=pk, clinic_id=clinic_ctx.clinic_id)

	if request.method == 'POST':
		form = FollowUpForm(request.POST, instance=followup)
		if form.is_valid():
			form.save()
			messages.success(request, 'Follow-up updated.')
			return redirect('dashboard')
	else:
		form = FollowUpForm(instance=followup)

	return render(request, 'tracker/followup_form.html', {'form': form, 'mode': 'edit', 'followup': followup})


@login_required
@require_POST
def followup_mark_done(request: HttpRequest, pk: int) -> HttpResponse:
	clinic_ctx = _get_user_clinic_context(request)
	followup = get_object_or_404(FollowUp, pk=pk, clinic_id=clinic_ctx.clinic_id)
	followup.status = FollowUp.Status.DONE
	followup.save(update_fields=['status', 'updated_at'])
	messages.success(request, 'Marked as done.')
	return redirect('dashboard')


def public_followup(request: HttpRequest, public_token: str) -> HttpResponse:
	followup = get_object_or_404(FollowUp, public_token=public_token)
	PublicViewLog.objects.create(
		followup=followup,
		user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:255],
		ip_address=_client_ip(request),
	)

	instructions = {
		FollowUp.Language.EN: [
			'Please follow the instructions from your clinic.',
			'If you have questions, contact the clinic using the phone number you already have.',
		],
		FollowUp.Language.HI: [
			'कृपया अपने क्लिनिक के निर्देशों का पालन करें।',
			'यदि कोई सवाल हो, तो क्लिनिक से संपर्क करें।',
		],
	}

	public_url = request.build_absolute_uri(reverse('public_followup', kwargs={'public_token': followup.public_token}))
	return render(
		request,
		'tracker/public_followup.html',
		{
			'followup': followup,
			'public_url': public_url,
			'instructions': instructions.get(followup.language, instructions[FollowUp.Language.EN]),
		},
	)
