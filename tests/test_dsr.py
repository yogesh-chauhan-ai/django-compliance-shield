"""
Tests for DataSubjectRequest model.
"""

import pytest
from unittest.mock import MagicMock
from django.utils import timezone


@pytest.mark.django_db
def test_dsr_deadline_india(django_user_model):
    from compliance_shield.models.dsr import DataSubjectRequest

    user    = django_user_model.objects.create_user(username='dsr1', password='pw')
    request = MagicMock()
    request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': ''}
    request.session = {}

    dsr = DataSubjectRequest.submit(
        user           = user,
        request_type   = 'access',
        jurisdiction   = 'IN',
        request_detail = 'Please send me my data.',
        request        = request,
    )

    assert dsr.deadline_days == 30
    assert dsr.deadline_at is not None
    delta = dsr.deadline_at - timezone.now()
    assert 29 <= delta.days <= 30


@pytest.mark.django_db
def test_dsr_deadline_us_ccpa(django_user_model):
    from compliance_shield.models.dsr import DataSubjectRequest

    user    = django_user_model.objects.create_user(username='dsr2', password='pw')
    request = MagicMock()
    request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': ''}
    request.session = {}

    dsr = DataSubjectRequest.submit(
        user='', request_type='access', jurisdiction='US',
        request_detail='Send my data.', request=request
    )
    dsr.user = user
    dsr.save()

    assert dsr.deadline_days == 45


@pytest.mark.django_db
def test_dsr_deadline_fcra_dispute(django_user_model):
    from compliance_shield.models.dsr import DataSubjectRequest

    user    = django_user_model.objects.create_user(username='dsr3', password='pw')
    request = MagicMock()
    request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': ''}
    request.session = {}

    dsr = DataSubjectRequest(
        user         = user,
        request_type = 'fcra_dispute',
        jurisdiction = 'US',
        request_detail = 'I dispute this.',
    )
    dsr.save()

    assert dsr.deadline_days == 30


@pytest.mark.django_db
def test_dsr_is_overdue(django_user_model):
    from compliance_shield.models.dsr import DataSubjectRequest
    from datetime import timedelta

    user = django_user_model.objects.create_user(username='dsr4', password='pw')
    dsr  = DataSubjectRequest.objects.create(
        user         = user,
        request_type = 'erasure',
        jurisdiction = 'IN',
        request_detail = 'Delete my data.',
        deadline_at  = timezone.now() - timedelta(days=1),
        status       = 'received',
    )
    assert dsr.is_overdue is True


@pytest.mark.django_db
def test_high_sensitivity_requires_identity_verification():
    from compliance_shield.models.dsr import DataSubjectRequest

    for rt in ['erasure', 'portability', 'fcra_dispute']:
        dsr = DataSubjectRequest(request_type=rt)
        assert dsr.requires_identity_verification is True

    dsr_low = DataSubjectRequest(request_type='correction')
    assert dsr_low.requires_identity_verification is False


@pytest.mark.django_db
def test_mark_completed(django_user_model):
    from compliance_shield.models.dsr import DataSubjectRequest

    user = django_user_model.objects.create_user(username='dsr5', password='pw')
    dsr  = DataSubjectRequest.objects.create(
        user=user, request_type='access', jurisdiction='IN',
        request_detail='Send data.', deadline_at=timezone.now()
    )
    dsr.mark_completed('Data sent via secure download link.')

    dsr.refresh_from_db()
    assert dsr.status == 'completed'
    assert dsr.response_detail == 'Data sent via secure download link.'
    assert dsr.completed_at is not None
