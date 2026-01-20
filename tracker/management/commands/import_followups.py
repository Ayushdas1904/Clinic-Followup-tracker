import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from tracker.models import FollowUp


@dataclass
class ImportStats:
    created: int = 0
    skipped: int = 0


class Command(BaseCommand):
    help = 'Import follow-ups from a CSV file for a specific user (clinic is derived from UserProfile).'

    def add_arguments(self, parser):
        parser.add_argument('--csv', required=True, help='Path to CSV file')
        parser.add_argument('--username', required=True, help='Username of the staff user who will own created follow-ups')

    def handle(self, *args, **options):
        csv_path = Path(options['csv']).expanduser().resolve()
        username = options['username']

        if not csv_path.exists():
            raise SystemExit(f'CSV file not found: {csv_path}')

        User = get_user_model()
        user = User.objects.filter(username=username).first()
        if not user:
            raise SystemExit(f'User not found: {username}')

        try:
            clinic_id = user.userprofile.clinic_id
        except Exception:
            raise SystemExit('UserProfile not found for this user. Create it and link a Clinic first.')

        stats = ImportStats()

        with csv_path.open('r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            required = {'patient_name', 'phone', 'language', 'due_date'}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                raise SystemExit(f'CSV must include columns: {sorted(required)}')

            for i, row in enumerate(reader, start=2):
                try:
                    patient_name = (row.get('patient_name') or '').strip()
                    phone = (row.get('phone') or '').strip()
                    language = (row.get('language') or '').strip().lower()
                    due_date_raw = (row.get('due_date') or '').strip()
                    notes = (row.get('notes') or '').strip()
                    status = (row.get('status') or FollowUp.Status.PENDING).strip().lower()

                    if not patient_name or not phone or not language or not due_date_raw:
                        raise ValueError('Missing required field(s).')

                    if language not in {FollowUp.Language.EN, FollowUp.Language.HI}:
                        raise ValueError('Invalid language (use en/hi).')

                    due = date.fromisoformat(due_date_raw)
                    if due < date.today():
                        raise ValueError('Due date cannot be in the past.')

                    if status not in {FollowUp.Status.PENDING, FollowUp.Status.DONE}:
                        raise ValueError('Invalid status (use pending/done).')

                    FollowUp.objects.create(
                        clinic_id=clinic_id,
                        created_by=user,
                        patient_name=patient_name,
                        phone=phone,
                        language=language,
                        notes=notes,
                        due_date=due,
                        status=status,
                    )
                    stats.created += 1
                except Exception as exc:
                    stats.skipped += 1
                    self.stderr.write(f'Row {i}: skipped ({exc})')

        self.stdout.write('Import complete')
        self.stdout.write(f'Created: {stats.created}')
        self.stdout.write(f'Skipped: {stats.skipped}')
