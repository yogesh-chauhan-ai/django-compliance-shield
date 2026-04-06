from django.apps import AppConfig


class ComplianceShieldConfig(AppConfig):
    name          = "compliance_shield"
    verbose_name  = "Compliance Shield"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        # Register system checks
        from compliance_shield import checks  # noqa: F401
