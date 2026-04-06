# Supported Field Types

The `@sensitive_field` decorator supports the following `field_type` values.

| field_type  | Use for                          | Default retention |
|-------------|----------------------------------|-------------------|
| `pan`       | India PAN number                 | 2y IN, 3y others  |
| `ssn`       | US Social Security Number        | 7 years           |
| `aadhaar`   | India Aadhaar number             | 2 years           |
| `passport`  | Passport number (any country)    | 3 years           |
| `gov_id`    | Generic government ID            | 3 years           |
| `dob`       | Date of birth                    | 3 years           |
| `financial` | Bank account, credit card        | 7 years           |
| `health`    | Medical records                  | 10 years          |
| `biometric` | Fingerprint, face ID             | 1 year            |
| `custom`    | Any other sensitive data         | 3 years           |

## Full decorator parameters

```python
@sensitive_field(
    field_type        = 'pan',        # See table above
    jurisdiction_field = 'data_region',# Model field holding region code
    masked_chars      = '*',           # Character used in masked property
    mask_keep_last    = 4,             # Characters to show at end of mask
    log_access        = True,          # Log every read to SensitiveDataAccessLog
    retention_days    = None,          # Override default retention (days)
    nullable          = True,          # Allow NULL in storage field
    blank             = True,          # Allow blank in storage field
)
```

## What gets created automatically

For `@sensitive_field(field_type='pan')` on field `pan_number`:

| Created                | Type        | Purpose                              |
|------------------------|-------------|--------------------------------------|
| `_pan_number`          | TextField   | Encrypted storage (db_column=pan_number) |
| `pan_number_index`     | CharField   | Blind index for search               |
| `pan_number`           | property    | Decrypt on get, encrypt on set       |
| `pan_number_masked`    | property    | e.g. `******1234F`                   |

## Example — multiple fields

```python
from django.db import models
from compliance_shield.decorators import sensitive_field


class UserProfile(models.Model):
    user        = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    country     = models.CharField(max_length=100, default='India')
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

    @sensitive_field(field_type='dob', jurisdiction_field='data_region',
                     mask_keep_last=4)
    class date_of_birth:
        pass

    @sensitive_field(field_type='custom', jurisdiction_field='data_region',
                     retention_days=365)
    class internal_employee_id:
        pass
```

## Searching encrypted fields

Always use the blind index — never filter on the encrypted storage field:

```python
from compliance_shield.encryption import RegionalEncryption

# Search by PAN
blind = RegionalEncryption.make_blind_index('ABCDE1234F', 'IN')
profile = UserProfile.objects.get(pan_number_index=blind)

# Exclude current instance (e.g. in forms)
qs = UserProfile.objects.filter(pan_number_index=blind).exclude(pk=instance.pk)
```
