"""
Tests for compliance_shield.middleware
"""

import pytest
from unittest.mock import MagicMock, patch
from django.test import RequestFactory


def _make_request(path='/', authenticated=False, staff=False):
    factory = RequestFactory()
    request = factory.get(path)
    request.session = {}
    if authenticated:
        user = MagicMock()
        user.is_authenticated = True
        user.is_staff         = staff
        user.is_superuser     = False
        request.user = user
    else:
        user = MagicMock()
        user.is_authenticated = False
        request.user = user
    return request


def test_compliance_headers_added():
    from compliance_shield.middleware import ComplianceMiddleware

    response = MagicMock()
    response.__setitem__ = MagicMock()

    def get_response(req):
        return response

    mw      = ComplianceMiddleware(get_response)
    request = _make_request()
    mw(request)

    # Headers should have been set
    calls = [call[0][0] for call in response.__setitem__.call_args_list]
    assert 'X-Data-Region' in calls
    assert 'X-Privacy-Policy-Version' in calls
    assert 'X-Frame-Options' in calls


def test_jurisdiction_defaults_to_in():
    from compliance_shield.middleware import ComplianceMiddleware

    response = MagicMock()
    response.__setitem__ = MagicMock()

    def get_response(req):
        return response

    mw      = ComplianceMiddleware(get_response)
    request = _make_request()
    mw(request)

    assert request.jurisdiction == 'IN'


def test_country_to_jurisdiction_mapping():
    from compliance_shield.middleware import COUNTRY_TO_JURISDICTION

    assert COUNTRY_TO_JURISDICTION['india']         == 'IN'
    assert COUNTRY_TO_JURISDICTION['united states'] == 'US'
    assert COUNTRY_TO_JURISDICTION['germany']       == 'EU'
    assert COUNTRY_TO_JURISDICTION['united kingdom']== 'UK'
    assert COUNTRY_TO_JURISDICTION['canada']        == 'CA'
    assert COUNTRY_TO_JURISDICTION['australia']     == 'AU'
    assert COUNTRY_TO_JURISDICTION['uae']           == 'AE'
    assert COUNTRY_TO_JURISDICTION['saudi arabia']  == 'SA'


def test_exempt_path_skips_consent_check():
    from compliance_shield.middleware import ComplianceMiddleware

    response = MagicMock()
    response.__setitem__ = MagicMock()

    def get_response(req):
        return response

    mw      = ComplianceMiddleware(get_response)
    request = _make_request(path='/compliance/consent/', authenticated=True)
    result  = mw(request)

    # Should not redirect — exempt path
    assert result == response


def test_staff_skips_consent_check():
    from compliance_shield.middleware import ComplianceMiddleware

    response = MagicMock()
    response.__setitem__ = MagicMock()

    def get_response(req):
        return response

    mw      = ComplianceMiddleware(get_response)
    request = _make_request(path='/dashboard/', authenticated=True, staff=True)
    result  = mw(request)

    assert result == response
