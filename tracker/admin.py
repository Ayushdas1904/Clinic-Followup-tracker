from django.contrib import admin

from .models import Clinic, FollowUp, PublicViewLog, UserProfile


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
	list_display = ('name', 'clinic_code', 'created_at')
	search_fields = ('name', 'clinic_code')
	readonly_fields = ('clinic_code', 'created_at')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
	list_display = ('user', 'clinic')
	search_fields = ('user__username', 'clinic__name', 'clinic__clinic_code')
	list_filter = ('clinic',)


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
	list_display = (
		'patient_name',
		'phone',
		'clinic',
		'due_date',
		'status',
		'language',
		'public_token',
		'created_at',
	)
	search_fields = ('patient_name', 'phone', 'public_token', 'clinic__name', 'clinic__clinic_code')
	list_filter = ('status', 'language', 'clinic', 'due_date')
	readonly_fields = ('public_token', 'created_at', 'updated_at')


@admin.register(PublicViewLog)
class PublicViewLogAdmin(admin.ModelAdmin):
	list_display = ('followup', 'viewed_at', 'ip_address')
	list_filter = ('viewed_at',)
	search_fields = ('followup__public_token', 'followup__patient_name', 'ip_address')
	readonly_fields = ('followup', 'viewed_at', 'user_agent', 'ip_address')
