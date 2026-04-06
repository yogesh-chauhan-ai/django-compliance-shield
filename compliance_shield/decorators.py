"""
@sensitive_field decorator for django-compliance-shield.

Transforms a placeholder class definition on a Django model into
a fully encrypted, searchable, masked, access-logged field — automatically.

Usage
-----
    from compliance_shield.decorators import sensitive_field

    class UserProfile(models.Model):
        data_region = models.CharField(max_length=10, default='IN')

        @sensitive_field(field_type='pan', jurisdiction_field='data_region')
        class pan_number:
            pass

        @sensitive_field(field_type='ssn', jurisdiction_field='data_region')
        class ssn_number:
            pass

What it creates automatically
------------------------------
    - _pan_number       TextField (encrypted storage)
    - pan_index         CharField (blind index for search)
    - pan_number        property (encrypt on set, decrypt on get)
    - pan_number_masked property (e.g. ******1234F)

Supported field_type values
----------------------------
    pan, ssn, aadhaar, passport, gov_id, dob, financial, health, biometric, custom
"""

from django.db import models


# ── Retention defaults per field type (days) ──────────────────────────────

FIELD_TYPE_RETENTION = {
    'pan':       {'IN': 365 * 2, 'default': 365 * 3},
    'ssn':       {'US': 365 * 7, 'default': 365 * 7},
    'aadhaar':   {'IN': 365 * 2, 'default': 365 * 2},
    'passport':  {'default': 365 * 3},
    'gov_id':    {'default': 365 * 3},
    'dob':       {'default': 365 * 3},
    'financial': {'default': 365 * 7},
    'health':    {'default': 365 * 10},
    'biometric': {'default': 365 * 1},
    'custom':    {'default': 365 * 3},
}


def sensitive_field(
    field_type='custom',
    jurisdiction_field='data_region',
    masked_chars='*',
    mask_keep_last=4,
    log_access=True,
    retention_days=None,
    nullable=True,
    blank=True,
):
    """
    Decorator that transforms a placeholder class into encrypted model fields.

    Parameters
    ----------
    field_type : str
        One of: pan, ssn, aadhaar, passport, gov_id, dob, financial,
        health, biometric, custom.
    jurisdiction_field : str
        Name of the field on the model that stores the data region
        (e.g. 'IN', 'US'). Used to select the correct encryption key.
    masked_chars : str
        Character used for masking (default '*').
    mask_keep_last : int
        Number of characters to show at the end of masked value (default 4).
    log_access : bool
        Whether to log every read to SensitiveDataAccessLog (default True).
    retention_days : int or None
        Override retention days. If None, uses FIELD_TYPE_RETENTION defaults.
    nullable : bool
        Whether the storage field allows NULL (default True).
    blank : bool
        Whether the storage field allows blank (default True).
    """

    def decorator(cls):
        # The name of the field is the class name e.g. pan_number
        field_name = cls.__name__

        # ── Descriptor that wires everything together ──────────────────────
        descriptor = _SensitiveFieldDescriptor(
            field_name      = field_name,
            field_type      = field_type,
            jurisdiction_field = jurisdiction_field,
            masked_chars    = masked_chars,
            mask_keep_last  = mask_keep_last,
            log_access      = log_access,
        )

        # ── Contribution to Django model via __init_subclass__ workaround ──
        # We store metadata on the class for ComplianceModelMixin to pick up
        if not hasattr(cls, '_compliance_sensitive_fields'):
            cls._compliance_sensitive_fields = {}

        cls._compliance_sensitive_fields[field_name] = {
            'field_type':         field_type,
            'jurisdiction_field': jurisdiction_field,
            'masked_chars':       masked_chars,
            'mask_keep_last':     mask_keep_last,
            'log_access':         log_access,
            'retention_days':     retention_days,
            'storage_field':      f'_{field_name}',
            'index_field':        f'{field_name}_index',
            'masked_property':    f'{field_name}_masked',
        }

        # Return a sentinel so ModelBase can detect decorated fields
        cls._is_sensitive_field = True
        cls._descriptor         = descriptor
        return cls

    return decorator


class _SensitiveFieldDescriptor:
    """
    Python descriptor that intercepts get/set on the model attribute.

    On SET  : encrypts the value, stores in _field_name, sets blind index.
    On GET  : decrypts from _field_name, logs access if enabled.
    """

    def __init__(self, field_name, field_type, jurisdiction_field,
                 masked_chars, mask_keep_last, log_access):
        self.field_name          = field_name
        self.field_type          = field_type
        self.jurisdiction_field  = jurisdiction_field
        self.masked_chars        = masked_chars
        self.mask_keep_last      = mask_keep_last
        self.log_access          = log_access
        self._storage_field      = f'_{field_name}'
        self._index_field        = f'{field_name}_index'

    def __set_name__(self, owner, name):
        self.field_name     = name
        self._storage_field = f'_{name}'
        self._index_field   = f'{name}_index'

    def _get_region(self, instance):
        return getattr(instance, self.jurisdiction_field, 'IN') or 'IN'

    def __get__(self, instance, owner):
        if instance is None:
            return self
        from compliance_shield.encryption import RegionalEncryption
        from compliance_shield.conf import cs_settings

        encrypted = getattr(instance, self._storage_field, None)
        value     = RegionalEncryption.decrypt(encrypted, self._get_region(instance))

        # Log access
        if self.log_access and cs_settings.LOG_SENSITIVE_ACCESS:
            self._log(instance, 'READ')

        return value

    def __set__(self, instance, value):
        from compliance_shield.encryption import RegionalEncryption

        region = self._get_region(instance)

        if value:
            encrypted = RegionalEncryption.encrypt(str(value), region)
            index     = RegionalEncryption.make_blind_index(str(value), region)
        else:
            encrypted = None
            index     = None

        # Write to the storage and index fields
        # Use object.__setattr__ to avoid recursion
        object.__setattr__(instance, self._storage_field, encrypted)
        try:
            object.__setattr__(instance, self._index_field, index)
        except AttributeError:
            pass

    def _log(self, instance, action):
        if not getattr(instance, 'pk', None):
            return
        try:
            from compliance_shield.models.audit import SensitiveDataAccessLog
            from django.utils import timezone
            SensitiveDataAccessLog.objects.create(
                model_label = instance.__class__._meta.label,
                object_id   = str(instance.pk),
                field_name  = self.field_name,
                field_type  = self.field_type,
                action      = action,
                accessed_at = timezone.now(),
            )
        except Exception:
            pass


class ComplianceModelMixin:
    """
    Optional mixin for models with @sensitive_field decorators.
    Provides the masked_<field> property automatically.

    Usage
    -----
        class UserProfile(ComplianceModelMixin, models.Model):
            ...
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        _apply_sensitive_fields(cls)


def _apply_sensitive_fields(model_class):
    """
    Called by ComplianceModelMixin.__init_subclass__.
    Inspects all class attributes for @sensitive_field decorated classes
    and wires up the descriptor + masked property + Django model fields.
    """
    for attr_name in list(vars(model_class)):
        attr = vars(model_class).get(attr_name)
        if not (isinstance(attr, type) and getattr(attr, '_is_sensitive_field', False)):
            continue

        meta    = attr._compliance_sensitive_fields.get(attr_name, {})
        desc    = attr._descriptor

        # Set the descriptor on the model class
        setattr(model_class, attr_name, desc)

        # Add Django storage field (_field_name = TextField)
        storage_name = f'_{attr_name}'
        if not any(f.name == storage_name for f in model_class._meta.fields
                   if hasattr(model_class, '_meta')):
            storage_field = models.TextField(
                null     = True,
                blank    = True,
                db_column = attr_name,
                verbose_name = f'{attr_name} (encrypted)',
            )
            storage_field.contribute_to_class(model_class, storage_name)

        # Add blind index field (field_name_index = CharField)
        index_name = f'{attr_name}_index'
        if not any(f.name == index_name for f in model_class._meta.fields
                   if hasattr(model_class, '_meta')):
            index_field = models.CharField(
                max_length   = 64,
                null         = True,
                blank        = True,
                db_index     = True,
                verbose_name = f'{attr_name} search index',
            )
            index_field.contribute_to_class(model_class, index_name)

        # Add masked property
        masked_name = f'{attr_name}_masked'
        keep_last   = meta.get('mask_keep_last', 4)
        mask_char   = meta.get('masked_chars', '*')

        def _make_masked_property(fn, kl, mc):
            def _masked(self):
                val = getattr(self, fn)
                if not val:
                    return None
                return mc * (len(val) - kl) + val[-kl:]
            return property(_masked)

        setattr(model_class, masked_name,
                _make_masked_property(attr_name, keep_last, mask_char))
