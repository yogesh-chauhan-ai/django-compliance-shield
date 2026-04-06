# Quick Start — django-compliance-shield

Get full global privacy compliance (DPDP, GDPR, CCPA, FCRA) running in under 10 minutes.

## 1. Install

```bash
pip install django-compliance-shield
```

## 2. Add to INSTALLED_APPS

```python
INSTALLED_APPS = [
    ...
    'compliance_shield',
]
```

## 3. Add middleware

```python
MIDDLEWARE = [
    ...
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'compliance_shield.middleware.ComplianceMiddleware',  # add here
    ...
]
```

## 4. Generate encryption keys

Run once per region. Store output in your `.env` file — never commit to version control.

```bash
python manage.py shell -c "from compliance_shield.encryption import generate_key; generate_key()"
```

Run for each region: IN, US, EU, UK, OTHER (fallback).

Generate blind index secrets (different from encryption keys):

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## 5. Configure settings

```python
COMPLIANCE_SHIELD = {
    # Encryption keys (one per region)
    'ENCRYPTION_KEY_IN':    env('ENCRYPTION_KEY_IN'),
    'ENCRYPTION_KEY_US':    env('ENCRYPTION_KEY_US'),
    'ENCRYPTION_KEY_EU':    env('ENCRYPTION_KEY_EU'),
    'ENCRYPTION_KEY_OTHER': env('ENCRYPTION_KEY_OTHER'),  # fallback

    # Blind index secrets (one per region, different from encryption keys)
    'BLIND_INDEX_SECRET_IN':    env('BLIND_INDEX_SECRET_IN'),
    'BLIND_INDEX_SECRET_US':    env('BLIND_INDEX_SECRET_US'),
    'BLIND_INDEX_SECRET_OTHER': env('BLIND_INDEX_SECRET_OTHER'),

    # Privacy policy version — bump when your policy changes
    'PRIVACY_POLICY_VERSION': 'v1.0.0',

    # Field on your user model that stores data region (e.g. 'IN', 'US')
    'JURISDICTION_FIELD': 'data_region',

    # Default jurisdiction when none can be detected
    'DEFAULT_JURISDICTION': 'IN',

    # Consents required before platform access
    'REQUIRED_CONSENTS': ['data_collection', 'data_processing'],
}
```

## 6. Include URLs

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    ...
    path('compliance/', include('compliance_shield.urls')),
]
```

## 7. Migrate and seed

```bash
python manage.py migrate
python manage.py compliance_setup
```

This creates all compliance tables and seeds 29 retention policies
across IN, US, EU, UK, CA, AU, AE, and SA.

## 8. Decorate your sensitive model fields

```python
from django.db import models
from compliance_shield.decorators import sensitive_field


class UserProfile(models.Model):
    user        = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    data_region = models.CharField(max_length=10, default='IN')

    @sensitive_field(field_type='pan', jurisdiction_field='data_region')
    class pan_number:
        pass

    @sensitive_field(field_type='ssn', jurisdiction_field='data_region')
    class ssn_number:
        pass

    @sensitive_field(field_type='passport', jurisdiction_field='data_region')
    class passport_number:
        pass
```

Then run:

```bash
python manage.py makemigrations
python manage.py migrate
```

## 9. Wire consent into registration

```python
from compliance_shield.utils import record_registration_consents

# In your registration view, after creating the user:
record_registration_consents(user, request, jurisdiction='IN')
```

## 10. Done

Your application now has:

- Field-level encryption with regional keys
- Blind index search on encrypted fields
- Automatic masked properties (e.g. `profile.pan_number_masked`)
- Consent management with audit trail
- Data subject rights (DSR) request handling
- Automatic response deadlines per jurisdiction
- Data retention policies enforced daily
- Breach notification deadline tracking
- Security headers on every response
- Django admin for all compliance models

## Next steps

- See [configuration.md](configuration.md) for all settings
- See [field-types.md](field-types.md) for supported field types
- See [jurisdictions.md](jurisdictions.md) for jurisdiction coverage

## Schedule daily retention enforcement

```bash
crontab -e
```

```
0 1 * * * cd /path/to/project && python manage.py enforce_retention
```
