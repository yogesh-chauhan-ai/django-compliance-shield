"""
django-compliance-shield
========================
Drop-in Django library for global privacy compliance.
Supports DPDP (India), GDPR (EU/UK), CCPA/FCRA (US), PIPEDA (Canada),
Privacy Act (Australia), and UAE/Saudi PDPL.

Basic usage
-----------
1. pip install django-compliance-shield
2. Add 'compliance_shield' to INSTALLED_APPS
3. Add 'compliance_shield.middleware.ComplianceMiddleware' to MIDDLEWARE
4. Configure COMPLIANCE_SHIELD in settings.py
5. Decorate sensitive model fields:

    from compliance_shield.decorators import sensitive_field

    class UserProfile(models.Model):
        data_region = models.CharField(max_length=10, default='IN')

        @sensitive_field(field_type='pan', jurisdiction_field='data_region')
        class pan_number:
            pass

6. python manage.py migrate
7. python manage.py compliance_setup

Author : Yogesh Chauhan <yogesh@pysquad.com>
License: MIT
"""

default_app_config = "compliance_shield.apps.ComplianceShieldConfig"

__version__ = "1.1.0"
__author__  = "Yogesh Chauhan"
__email__   = "yogesh@pysquad.com"
__license__ = "MIT"

# Public API
from compliance_shield.decorators import sensitive_field  # noqa: F401

__all__ = [
    "sensitive_field",
    "__version__",
]
