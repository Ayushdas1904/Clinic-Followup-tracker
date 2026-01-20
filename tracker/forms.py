import re

from django import forms
from django.utils import timezone

from .models import FollowUp


_PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")


class FollowUpForm(forms.ModelForm):
    class Meta:
        model = FollowUp
        fields = ['patient_name', 'phone', 'language', 'notes', 'due_date', 'status']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_phone(self) -> str:
        phone = (self.cleaned_data.get('phone') or '').strip()
        if not _PHONE_RE.match(phone):
            raise forms.ValidationError('Enter a valid phone number (7–15 digits, optional +).')
        return phone

    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date < timezone.localdate():
            raise forms.ValidationError('Due date cannot be in the past.')
        return due_date
