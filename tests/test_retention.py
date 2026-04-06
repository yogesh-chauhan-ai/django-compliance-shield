"""
Tests for compliance_shield retention models and setup command.
"""

import pytest


@pytest.mark.django_db
def test_compliance_setup_seeds_policies():
    from compliance_shield.models.retention import DataRetentionPolicy
    from compliance_shield.management.commands.compliance_setup import Command, POLICIES

    cmd = Command()
    cmd.stdout = __import__('io').StringIO()
    cmd.style  = __import__('django.core.management.color', fromlist=['color']).color_style()
    cmd.handle(overwrite=False)

    assert DataRetentionPolicy.objects.count() == len(POLICIES)


@pytest.mark.django_db
def test_us_fcra_retention_is_7_years():
    from compliance_shield.models.retention import DataRetentionPolicy
    from compliance_shield.management.commands.compliance_setup import Command

    cmd = Command()
    cmd.stdout = __import__('io').StringIO()
    cmd.style  = __import__('django.core.management.color', fromlist=['color']).color_style()
    cmd.handle(overwrite=False)

    policy = DataRetentionPolicy.objects.get(
        jurisdiction='US', data_category='employment_records'
    )
    assert policy.retention_days == 365 * 7
    assert policy.action_on_expiry == 'anonymise'


@pytest.mark.django_db
def test_in_dpdp_pan_retention_is_2_years():
    from compliance_shield.models.retention import DataRetentionPolicy
    from compliance_shield.management.commands.compliance_setup import Command

    cmd = Command()
    cmd.stdout = __import__('io').StringIO()
    cmd.style  = __import__('django.core.management.color', fromlist=['color']).color_style()
    cmd.handle(overwrite=False)

    policy = DataRetentionPolicy.objects.get(
        jurisdiction='IN', data_category='pan_aadhaar'
    )
    assert policy.retention_days == 365 * 2


@pytest.mark.django_db
def test_setup_is_idempotent():
    from compliance_shield.models.retention import DataRetentionPolicy
    from compliance_shield.management.commands.compliance_setup import Command, POLICIES

    for _ in range(3):
        cmd = Command()
        cmd.stdout = __import__('io').StringIO()
        cmd.style  = __import__('django.core.management.color', fromlist=['color']).color_style()
        cmd.handle(overwrite=False)

    # Running 3 times should not create duplicates
    assert DataRetentionPolicy.objects.count() == len(POLICIES)
