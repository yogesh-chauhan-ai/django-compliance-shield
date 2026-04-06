"""
python manage.py compliance_setup

Seeds the DataRetentionPolicy table with jurisdiction defaults.
Safe to run multiple times. Run once after installation.
"""

from django.core.management.base import BaseCommand
from compliance_shield.models.retention import DataRetentionPolicy


POLICIES = [
    # ── India DPDP ────────────────────────────────────────────────────────
    {'jurisdiction': 'IN', 'data_category': 'employment_records',
     'retention_days': 365*3, 'action_on_expiry': 'anonymise',
     'legal_basis': 'DPDP Act 2025 Section 8(7) — retain only as long as necessary'},
    {'jurisdiction': 'IN', 'data_category': 'pan_aadhaar',
     'retention_days': 365*2, 'action_on_expiry': 'anonymise',
     'legal_basis': 'DPDP Act 2025 — sensitive personal data minimisation'},
    {'jurisdiction': 'IN', 'data_category': 'consent_records',
     'retention_days': 365*7, 'action_on_expiry': 'archive',
     'legal_basis': 'DPDP Act 2025 — consent audit trail required'},
    {'jurisdiction': 'IN', 'data_category': 'audit_logs',
     'retention_days': 365*5, 'action_on_expiry': 'archive',
     'legal_basis': 'DPDP Act 2025 — accountability and audit'},
    {'jurisdiction': 'IN', 'data_category': 'session_data',
     'retention_days': 30, 'action_on_expiry': 'delete',
     'legal_basis': 'DPDP Act 2025 — data minimisation'},
    {'jurisdiction': 'IN', 'data_category': 'communication_logs',
     'retention_days': 365*2, 'action_on_expiry': 'anonymise',
     'legal_basis': 'DPDP Act 2025 — retain only as long as necessary'},

    # ── United States FCRA / CCPA ─────────────────────────────────────────
    {'jurisdiction': 'US', 'data_category': 'employment_records',
     'retention_days': 365*7, 'action_on_expiry': 'anonymise',
     'legal_basis': 'FCRA 15 USC 1681c — 7 year reporting period'},
    {'jurisdiction': 'US', 'data_category': 'ssn',
     'retention_days': 365*7, 'action_on_expiry': 'anonymise',
     'legal_basis': 'FCRA 15 USC 1681c — 7 year retention'},
    {'jurisdiction': 'US', 'data_category': 'consent_records',
     'retention_days': 365*7, 'action_on_expiry': 'archive',
     'legal_basis': 'FCRA — authorisation records must match report retention'},
    {'jurisdiction': 'US', 'data_category': 'audit_logs',
     'retention_days': 365*7, 'action_on_expiry': 'archive',
     'legal_basis': 'CCPA / FCRA — audit trail'},
    {'jurisdiction': 'US', 'data_category': 'session_data',
     'retention_days': 30, 'action_on_expiry': 'delete',
     'legal_basis': 'CCPA — data minimisation'},

    # ── European Union GDPR ───────────────────────────────────────────────
    {'jurisdiction': 'EU', 'data_category': 'employment_records',
     'retention_days': 365*3, 'action_on_expiry': 'anonymise',
     'legal_basis': 'GDPR Article 5(1)(e) — storage limitation'},
    {'jurisdiction': 'EU', 'data_category': 'consent_records',
     'retention_days': 365*5, 'action_on_expiry': 'archive',
     'legal_basis': 'GDPR Article 7(1) — demonstrate consent was given'},
    {'jurisdiction': 'EU', 'data_category': 'audit_logs',
     'retention_days': 365*5, 'action_on_expiry': 'archive',
     'legal_basis': 'GDPR Article 5(2) — accountability principle'},
    {'jurisdiction': 'EU', 'data_category': 'session_data',
     'retention_days': 30, 'action_on_expiry': 'delete',
     'legal_basis': 'GDPR Article 5(1)(c) — data minimisation'},

    # ── United Kingdom UK GDPR ────────────────────────────────────────────
    {'jurisdiction': 'UK', 'data_category': 'employment_records',
     'retention_days': 365*3, 'action_on_expiry': 'anonymise',
     'legal_basis': 'UK GDPR Article 5(1)(e) — storage limitation'},
    {'jurisdiction': 'UK', 'data_category': 'consent_records',
     'retention_days': 365*5, 'action_on_expiry': 'archive',
     'legal_basis': 'UK GDPR Article 7(1) — demonstrate consent'},
    {'jurisdiction': 'UK', 'data_category': 'audit_logs',
     'retention_days': 365*5, 'action_on_expiry': 'archive',
     'legal_basis': 'UK GDPR Article 5(2) — accountability'},
    {'jurisdiction': 'UK', 'data_category': 'session_data',
     'retention_days': 30, 'action_on_expiry': 'delete',
     'legal_basis': 'UK GDPR Article 5(1)(c) — data minimisation'},

    # ── Canada PIPEDA ─────────────────────────────────────────────────────
    {'jurisdiction': 'CA', 'data_category': 'employment_records',
     'retention_days': 365*3, 'action_on_expiry': 'anonymise',
     'legal_basis': 'PIPEDA Principle 5 — limiting use and retention'},
    {'jurisdiction': 'CA', 'data_category': 'consent_records',
     'retention_days': 365*5, 'action_on_expiry': 'archive',
     'legal_basis': 'PIPEDA Principle 3 — consent'},
    {'jurisdiction': 'CA', 'data_category': 'audit_logs',
     'retention_days': 365*5, 'action_on_expiry': 'archive',
     'legal_basis': 'PIPEDA Principle 1 — accountability'},

    # ── Australia Privacy Act ─────────────────────────────────────────────
    {'jurisdiction': 'AU', 'data_category': 'employment_records',
     'retention_days': 365*3, 'action_on_expiry': 'anonymise',
     'legal_basis': 'Privacy Act 1988 APP 11 — security of personal information'},
    {'jurisdiction': 'AU', 'data_category': 'consent_records',
     'retention_days': 365*5, 'action_on_expiry': 'archive',
     'legal_basis': 'Privacy Act 1988 APP 11'},
    {'jurisdiction': 'AU', 'data_category': 'audit_logs',
     'retention_days': 365*5, 'action_on_expiry': 'archive',
     'legal_basis': 'Privacy Act 1988 APP 11'},

    # ── UAE PDPL ──────────────────────────────────────────────────────────
    {'jurisdiction': 'AE', 'data_category': 'employment_records',
     'retention_days': 365*3, 'action_on_expiry': 'anonymise',
     'legal_basis': 'UAE Federal Decree-Law No.45/2021 — data minimisation'},
    {'jurisdiction': 'AE', 'data_category': 'consent_records',
     'retention_days': 365*5, 'action_on_expiry': 'archive',
     'legal_basis': 'UAE Federal Decree-Law No.45/2021 — consent records'},

    # ── Saudi Arabia PDPL ─────────────────────────────────────────────────
    {'jurisdiction': 'SA', 'data_category': 'employment_records',
     'retention_days': 365*3, 'action_on_expiry': 'anonymise',
     'legal_basis': 'Saudi PDPL — data minimisation and retention'},
    {'jurisdiction': 'SA', 'data_category': 'consent_records',
     'retention_days': 365*5, 'action_on_expiry': 'archive',
     'legal_basis': 'Saudi PDPL — consent documentation'},
]


class Command(BaseCommand):
    help = 'Seeds DataRetentionPolicy with jurisdiction defaults. Safe to run multiple times.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--overwrite', action='store_true',
            help='Overwrite existing policies with defaults'
        )

    def handle(self, *args, **options):
        overwrite = options.get('overwrite', False)
        created = skipped = updated = 0

        from compliance_shield.conf import cs_settings, is_jurisdiction_enabled

        enabled = cs_settings.ENABLED_JURISDICTIONS
        if enabled:
            self.stdout.write(
                f'ENABLED_JURISDICTIONS set — seeding only: {", ".join(enabled)}'
            )

        for p in POLICIES:
            # Skip jurisdictions not in ENABLED_JURISDICTIONS (if set)
            if not is_jurisdiction_enabled(p['jurisdiction']):
                skipped += 1
                continue

            existing = DataRetentionPolicy.objects.filter(
                data_category=p['data_category'],
                jurisdiction=p['jurisdiction'],
            ).first()

            if existing:
                if overwrite:
                    for k, v in p.items():
                        setattr(existing, k, v)
                    existing.reviewed_by = 'compliance_setup'
                    existing.save()
                    updated += 1
                else:
                    skipped += 1
            else:
                DataRetentionPolicy.objects.create(**p, reviewed_by='compliance_setup')
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nCompliance setup complete.\n'
            f'  Policies created : {created}\n'
            f'  Policies updated : {updated}\n'
            f'  Policies skipped : {skipped}\n\n'
            f'Next steps:\n'
            f'  1. Generate encryption keys:\n'
            f'     python manage.py shell -c '
            f'"from compliance_shield.encryption import generate_key; generate_key()"\n'
            f'  2. Add keys to your COMPLIANCE_SHIELD settings\n'
            f'  3. Add ComplianceMiddleware to MIDDLEWARE\n'
            f'  4. Include compliance_shield.urls in your urls.py\n'
        ))
