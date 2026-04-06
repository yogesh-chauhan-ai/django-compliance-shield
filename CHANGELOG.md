# Changelog

All notable changes to django-compliance-shield will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [1.1.0] — 2026-04-06

### Added
- `ENABLED_JURISDICTIONS` setting — restrict compliance enforcement to specific countries
- `EMAIL_NOTIFICATIONS` master switch with full recipient configuration
- `DSR_ALERT_RECIPIENTS` — privacy team notified on every new DSR
- `BREACH_ALERT_RECIPIENTS` — DPO and legal notified on every new breach
- `OVERDUE_DSR_RECIPIENTS` — daily digest of overdue DSRs from enforce_retention cron
- `DSR_USER_CONFIRMATION_EMAIL` — toggle user-facing DSR emails
- `EMAIL_FROM` — dedicated from address for compliance emails
- `notifications.py` — central email notification module (silent-fail)
- `serializers.py` — DRF serializers for all compliance models
- `api_views.py` — DRF API views for consent, DSR, access log, retention, jurisdiction
- `api_urls.py` — DRF URL routing (include alongside or instead of template urls)
- Breach notification auto-fires on `DataBreachRecord` creation
- DSR completion and rejection emails auto-fire on status change
- Consent withdrawal email notification to privacy team
- Middleware consent gate now skips jurisdictions not in `ENABLED_JURISDICTIONS`
- `compliance_setup` command only seeds policies for enabled jurisdictions

### Changed
- `conf.py` docstring expanded with full settings reference
- `urls.py` docstring updated to document both template and DRF usage
- `README.md` updated with new features section

---

## [1.0.0] — 2026-04-06

### Added
- `@sensitive_field` decorator for automatic field-level encryption on Django models
- Regional Fernet encryption with separate keys per jurisdiction (IN, US, EU, UK, CA, AU, AE, SA)
- Blind index generation for searching encrypted fields without decryption
- Automatic masked property generation (`field_name_masked`)
- `SensitiveDataAccessLog` — immutable audit log of every field read
- `ConsentRecord` — full consent lifecycle with exact text, version, IP, and timestamp
- `DataDeletionRequest` — auto-created on consent withdrawal
- `DataSubjectRequest` — handles all data subject rights with auto-calculated deadlines
- `DataRetentionPolicy` and `DataRetentionLog` — 29 jurisdiction policies seeded out of the box
- `DataBreachRecord` — breach notification deadline tracking per jurisdiction
- `ComplianceMiddleware` — jurisdiction detection, consent gating, security headers
- Consent and privacy settings views with overridable templates
- Django admin for all compliance models with bulk actions
- Management commands: `compliance_setup`, `enforce_retention`, `rotate_keys`
- Django system checks (W001–W004) for configuration validation
- Full test suite (encryption, consent, middleware, retention, DSR)
- Documentation: quickstart, configuration, field types, jurisdictions

### Jurisdictions covered
DPDP (India), GDPR (EU), UK GDPR, CCPA/FCRA (US), PIPEDA (Canada),
Privacy Act (Australia), UAE PDPL, Saudi Arabia PDPL

### Django versions tested
3.2, 4.2, 5.0, 5.1

### Python versions tested
3.9, 3.10, 3.11, 3.12
