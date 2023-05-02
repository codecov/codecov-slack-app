import os
from unittest import TestCase

import pytest
from rest_framework.exceptions import ValidationError

from core.enums import EndpointName
from service_auth.helpers import (_user_info, get_endpoint_details,
                                  validate_gh_call_params)


def test_user_info():
    user_info = {
        "user": {
            "name": "user",
            "profile": {
                "email": "user@example.com",
                "display_name": "Test User",
            },
            "team_id": "12345",
            "is_bot": False,
            "is_owner": True,
            "is_admin": False,
        }
    }
    expected_output = {
        "username": "user",
        "email": "user@example.com",
        "display_name": "Test User",
        "team_id": "12345",
        "is_bot": False,
        "is_owner": True,
        "is_admin": False,
    }
    assert _user_info(user_info) == expected_output


def test_validate_gh_call_params():
    with pytest.raises(ValidationError) as e:
        validate_gh_call_params(code=None, state="12345")

    with pytest.raises(ValidationError) as e:
        validate_gh_call_params(code="12345", state=None)

    validate_gh_call_params(code="12345", state="12345")


class TestGetEndpointDetails(TestCase):
    def setUp(self):
        self.endpoint = EndpointName.REPOS
        self.params_dict = {"username": "codecov"}
        self.service = "gh"

    def test_get_endpoint_details(self):
        os.environ["CODECOV_PUBLIC_API"] = "https://codecov.io/api/"

        endpoint = get_endpoint_details(
            endpoint_name=self.endpoint,
            service=self.service,
            params_dict=self.params_dict,
        )
        self.assertEqual(endpoint.url, "None/gh/codecov/repos/")
        self.assertEqual(endpoint.is_private, False)

    def test_get_endpoint_details_with_optional_params(self):
        os.environ["CODECOV_PUBLIC_API"] = "https://codecov.io/api/"

        endpoint = get_endpoint_details(
            endpoint_name=self.endpoint,
            service=self.service,
            params_dict=self.params_dict,
            optional_params={"page_size": "99"},
        )
        self.assertEqual(endpoint.url, "None/gh/codecov/repos/?page_size=99")
        self.assertEqual(endpoint.is_private, False)

    def test_get_endpoint_details_is_private(self):
        os.environ["CODECOV_PUBLIC_API"] = "https://codecov.io/api/"

        endpoint = get_endpoint_details(
            endpoint_name=EndpointName.SERVICE_OWNERS,
            service=self.service,
            params_dict=self.params_dict,
        )
        self.assertEqual(endpoint.url, "None/gh/")
        self.assertEqual(endpoint.is_private, True)
