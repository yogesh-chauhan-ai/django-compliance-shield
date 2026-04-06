"""
python manage.py enforce_retention [--dry-run] [--jurisdiction IN]

Enforces data retention policies by anonymising or deleting expired records.
Schedule daily via cron:
    0 1 * * * cd /path/to/project && python manage.py enforce_retention
"""

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from compliance_shield.models.retention import DataRetentionPolicy, DataRetentionLog


class Command(BaseCommand):
    help = 'Enforces data retention policies. Schedule daily via cron.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be affected without modifying data'
        )
        parser.add_argument(
            '--jurisdiction', type=str,
            help='Run only for a specific jurisdiction e.g. --jurisdiction IN'
        )

    def handle(self, *args, **options):
        dry_run      = options.get('dry_run', False)
        jurisdiction = options.get('jurisdiction')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no data will be modified\n'))

        policies = DataRetentionPolicy.objects.filter(is_active=True)
        if jurisdiction:
            policies = policies.filter(jurisdiction=jurisdiction)

        for policy in policies:
            self._enforce(policy, dry_run)

        self.stdout.write(self.style.SUCCESS('\nRetention enforcement complete.'))

    def _enforce(self, policy, dry_run):
        cutoff  = timezone.now() - timedelta(days=policy.retention_days)
        handler = self._get_handler(policy.data_category)

        if not handler:
            return

        try:
            count = handler(policy, cutoff, dry_run)
            label = 'Would affect' if dry_run else 'Affected'
            self.stdout.write(
                f'  {label} {count} records | {policy.jurisdiction} | '
                f'{policy.data_category} | {policy.action_on_expiry}'
            )
            if not dry_run:
                DataRetentionLog.objects.create(
                    data_category    = policy.data_category,
                    jurisdiction     = policy.jurisdiction,
                    action_taken     = policy.action_on_expiry + 'd'
                                       if not policy.action_on_expiry.endswith('d')
                                       else policy.action_on_expiry,
                    records_affected = count,
                    policy           = policy,
                    run_by           = 'system',
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'  Error: {policy.jurisdiction} | {policy.data_category}: {e}'
                )
            )
            if not dry_run:
                DataRetentionLog.objects.create(
                    data_category = policy.data_category,
                    jurisdiction  = policy.jurisdiction,
                    action_taken  = 'flagged',
                    policy        = policy,
                    run_by        = 'system',
                    errors        = str(e),
                )

    def _get_handler(self, data_category):
        return {
            'session_data': self._handle_sessions,
        }.get(data_category)

    def _handle_sessions(self, policy, cutoff, dry_run):
        """Hard delete expired Django sessions."""
        try:
            from django.contrib.sessions.models import Session
            expired = Session.objects.filter(expire_date__lt=cutoff)
            count   = expired.count()
            if not dry_run and count > 0:
                expired.delete()
            return count
        except Exception:
            return 0
