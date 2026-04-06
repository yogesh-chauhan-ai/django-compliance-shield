# django-compliance-shield

> Drop-in Django library for global privacy compliance.
> One decorator. Full DPDP, GDPR, CCPA, FCRA compliance.

[![PyPI version](https://badge.fury.io/py/django-compliance-shield.svg)](https://pypi.org/project/django-compliance-shield/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Django](https://img.shields.io/badge/Django-3.2%20%7C%204.2%20%7C%205.0-blue)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)

---

## What it does

Add one decorator to your model. The library handles everything else.

```python
from compliance_shield.decorators import sensitive_field

class UserProfile(models.Model):
    data_region = models.CharField(max_length=10, default='IN')

    @sensitive_field(field_type='pan', jurisdiction_field='data_region')
    class pan_number:
        pass

    @sensitive_field(field_type='ssn', jurisdiction_field='data_region')
    class ssn_number:
        pass
```

That is all you write. The library automatically creates:

| Created                | What it does                                        |
|------------------------|-----------------------------------------------------|
| `_pan_number`          | Encrypted storage field (Fernet, regional key)      |
| `pan_number_index`     | Blind index for search without decryption           |
| `pan_number`           | Property — decrypts on get, encrypts on set         |
| `pan_number_masked`    | Property — e.g. `******1234F`                       |
| Access log entry       | Every read logged to `SensitiveDataAccessLog`       |

---

## Features

**Encryption**
- Field-level Fernet encryption with separate keys per jurisdiction
- Blind index for searching encrypted fields
- Auto-masked property (`field_masked`)
- Key rotation via `python manage.py rotate_keys`
- MultiFernet supports zero-downtime key rotation

**Consent Management**
- `ConsentRecord` stores exact text shown, version, IP, timestamp
- Consent gate middleware — redirects to consent page if required consents missing
- Withdraw consent — triggers `DataDeletionRequest` automatically
- Privacy settings page — users manage all consents in one place

**Data Subject Rights**
- `DataSubjectRequest` handles all rights across all jurisdictions
- Auto-calculated deadlines: IN=30d, US access=45d, FCRA=30d, EU=30d
- High-sensitivity requests require identity verification
- DSR confirmation email sent automatically

**Data Retention**
- 29 retention policies seeded out of the box
- Daily enforcement: `python manage.py enforce_retention`
- `DataRetentionLog` — immutable audit trail of every enforcement action
- Legal hold flag prevents deletion of records under investigation

**Breach Notification**
- `DataBreachRecord` tracks every breach
- Authority notification deadlines per jurisdiction (72h IN/EU/UK/US, 30d AU)
- Admin dashboard shows overdue notifications in red

**Compliance Middleware**
- Jurisdiction detection on every request
- Security headers: `X-Data-Region`, `X-Frame-Options`, `X-Content-Type-Options`,
  `Referrer-Policy`, `Permissions-Policy`, `Strict-Transport-Security`

**Django Admin**
- Admin registration for all 7 compliance models
- Bulk actions: mark DSR in progress / completed, mark breach contained / resolved
- Consent records and access logs are permanently read-only

---

## Jurisdiction coverage

| Code  | Law                   | DSR Deadline | Breach Deadline  |
|-------|-----------------------|-------------|-----------------|
| IN    | DPDP Act 2025         | 30 days     | 72 hours        |
| US    | CCPA / FCRA           | 45 days     | 72 hours        |
| EU    | GDPR                  | 30 days     | 72 hours        |
| UK    | UK GDPR               | 30 days     | 72 hours        |
| CA    | PIPEDA                | 30 days     | ASAP            |
| AU    | Privacy Act 1988      | 30 days     | 30 days         |
| AE    | UAE PDPL              | 30 days     | 72 hours        |
| SA    | Saudi Arabia PDPL     | 30 days     | 72 hours        |

---

## What's new in v1.0.0

### 1. Jurisdiction control — enable only the countries you need

```python
COMPLIANCE_SHIELD = {
    # Only activate India and USA compliance.
    # Consent gate, retention policies, DSR types, and breach deadlines
    # will only apply to these two jurisdictions.
    'ENABLED_JURISDICTIONS': ['IN', 'US'],  # None = all (default)
}
```

`python manage.py compliance_setup` will only seed policies for enabled jurisdictions.
The middleware consent gate will only fire for users in enabled jurisdictions.
The privacy settings page will only show DSR types relevant to enabled jurisdictions.

---

### 2. Email notifications — fully configurable

```python
COMPLIANCE_SHIELD = {
    'EMAIL_NOTIFICATIONS': True,           # master switch (default: False)
    'EMAIL_FROM': 'compliance@co.com',     # defaults to DEFAULT_FROM_EMAIL

    # Who gets notified when a user submits a DSR
    'DSR_ALERT_RECIPIENTS': ['privacy@co.com'],

    # Who gets notified immediately when a breach is recorded
    'BREACH_ALERT_RECIPIENTS': ['dpo@co.com', 'legal@co.com'],

    # Who gets the daily overdue DSR digest (from enforce_retention cron)
    'OVERDUE_DSR_RECIPIENTS': ['privacy@co.com'],

    # Whether to email the user on DSR submit / complete / reject
    'DSR_USER_CONFIRMATION_EMAIL': True,
}
```

All notifications use Django's standard email backend.
Silent fail — a misconfigured email backend will never crash the compliance system.

---

### 3. DRF support — works with React, Vue, mobile, and headless projects

```python
# urls.py — use template views, API views, or both
urlpatterns = [
    path('compliance/', include('compliance_shield.urls')),         # template views
    path('api/compliance/', include('compliance_shield.api_urls')), # DRF API views
]
```

Available API endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/compliance/consent/` | Current consent status |
| POST | `/api/compliance/consent/grant/` | Grant one or more consents |
| POST | `/api/compliance/consent/withdraw/` | Withdraw a consent |
| GET | `/api/compliance/dsr/` | List my DSRs |
| POST | `/api/compliance/dsr/submit/` | Submit a new DSR |
| GET | `/api/compliance/access-log/` | Sensitive data access log |
| GET | `/api/compliance/retention/` | View retention policies |
| GET | `/api/compliance/jurisdiction/` | Current jurisdiction info |

All endpoints require authentication. All return JSON.

---

## Quick start

```bash
pip install django-compliance-shield
```

```python
# settings.py
INSTALLED_APPS = [..., 'compliance_shield']

MIDDLEWARE = [
    ...
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'compliance_shield.middleware.ComplianceMiddleware',
    ...
]

COMPLIANCE_SHIELD = {
    'ENCRYPTION_KEY_IN':    env('ENCRYPTION_KEY_IN'),
    'ENCRYPTION_KEY_US':    env('ENCRYPTION_KEY_US'),
    'ENCRYPTION_KEY_EU':    env('ENCRYPTION_KEY_EU'),
    'ENCRYPTION_KEY_OTHER': env('ENCRYPTION_KEY_OTHER'),
    'BLIND_INDEX_SECRET_IN':    env('BLIND_INDEX_SECRET_IN'),
    'BLIND_INDEX_SECRET_OTHER': env('BLIND_INDEX_SECRET_OTHER'),
    'PRIVACY_POLICY_VERSION': 'v1.0.0',
    'DEFAULT_JURISDICTION': 'IN',
    'REQUIRED_CONSENTS': ['data_collection', 'data_processing'],
}
```

```python
# urls.py
urlpatterns = [
    ...
    path('compliance/', include('compliance_shield.urls')),
]
```

```bash
python manage.py migrate
python manage.py compliance_setup
```

Wire consent into registration:

```python
from compliance_shield.utils import record_registration_consents
record_registration_consents(user, request, jurisdiction='IN')
```

See [docs/quickstart.md](docs/quickstart.md) for the full guide.

---

## Supported field types

`pan` `ssn` `aadhaar` `passport` `gov_id` `dob` `financial` `health` `biometric` `custom`

See [docs/field-types.md](docs/field-types.md) for full reference.

---

## Requirements

- Python 3.9+
- Django 3.2, 4.2, or 5.0+
- `cryptography>=41.0.0`

---

## Management commands

| Command | Description |
|---------|-------------|
| `python manage.py compliance_setup` | Seed 29 retention policies |
| `python manage.py enforce_retention` | Enforce retention (run daily) |
| `python manage.py enforce_retention --dry-run` | Preview without changes |
| `python manage.py enforce_retention --jurisdiction IN` | Single jurisdiction |
| `python manage.py rotate_keys --model app.Model --field pan_number` | Rotate encryption key |

---

## Author

**Yogesh Chauhan** — AI and Django engineer, Ahmedabad, India.

[GitHub](https://github.com/yogesh-chauhan-ai) |
[LinkedIn](https://linkedin.com/in/yogesh-python-ai) |
[Portfolio](https://yogesh-python-ai.github.io)

---

## License

MIT — see [LICENSE](LICENSE).
