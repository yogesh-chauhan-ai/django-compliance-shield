"""
Tests for compliance_shield consent models.
"""

import pytest
from unittest.mock import MagicMock, patch
from django.utils import timezone


@pytest.mark.django_db
def test_record_consent_creates_record(django_user_model):
    from compliance_shield.models.consent import ConsentRecord

    user    = django_user_model.objects.create_user(username='u1', password='pw')
    request = MagicMock()
    request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'TestAgent'}
    request.session = {'session_key': 'abc123'}

    record = ConsentRecord.record_consent(
        user         = user,
        consent_type = 'data_collection',
        jurisdiction = 'IN',
        consent_text = 'I agree to data collection.',
        request      = request,
    )

    assert record.pk is not None
    assert record.granted is True
    assert record.granted_at is not None
    assert record.consent_text_hash != ''
    assert record.ip_address == '127.0.0.1'


@pytest.mark.django_db
def test_has_valid_consent_true(django_user_model):
    from compliance_shield.models.consent import ConsentRecord

    user    = django_user_model.objects.create_user(username='u2', password='pw')
    request = MagicMock()
    request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': ''}
    request.session = {}

    ConsentRecord.record_consent(
        user='', consent_type='data_processing', jurisdiction='IN',
        consent_text='I agree.', request=request
    )
    ConsentRecord.objects.filter().update(user=user)

    # Re-create properly
    ConsentRecord.objects.all().delete()
    ConsentRecord.record_consent(
        user=user, consent_type='data_processing', jurisdiction='IN',
        consent_text='I agree.', request=request
    )

    assert ConsentRecord.has_valid_consent(user, 'data_processing', 'IN') is True


@pytest.mark.django_db
def test_has_valid_consent_false_when_no_record(django_user_model):
    from compliance_shield.models.consent import ConsentRecord

    user = django_user_model.objects.create_user(username='u3', password='pw')
    assert ConsentRecord.has_valid_consent(user, 'marketing', 'IN') is False


@pytest.mark.django_db
def test_withdraw_consent_creates_deletion_request(django_user_model):
    from compliance_shield.models.consent import ConsentRecord, DataDeletionRequest

    user    = django_user_model.objects.create_user(username='u4', password='pw')
    request = MagicMock()
    request.META = {'REMOTE_ADDR': '10.0.0.1', 'HTTP_USER_AGENT': ''}
    request.session = {}

    ConsentRecord.record_consent(
        user=user, consent_type='marketing', jurisdiction='IN',
        consent_text='I agree to marketing.', request=request
    )

    assert ConsentRecord.has_valid_consent(user, 'marketing', 'IN') is True

    ConsentRecord.withdraw_consent(user, 'marketing', 'IN', request)

    assert ConsentRecord.has_valid_consent(user, 'marketing', 'IN') is False
    assert DataDeletionRequest.objects.filter(
        user=user, consent_type='marketing'
    ).exists()
