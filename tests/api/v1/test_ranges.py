import copy
import json
import uuid

import pytest
from fastapi import status
from httpx import AsyncClient

from src.app.models.template_range_model import TemplateRangeModel
from src.app.schemas.template_host_schema import TemplateHostSchema
from src.app.schemas.template_subnet_schema import TemplateSubnetHeaderSchema

from .config import (
    BASE_ROUTE,
    base_user_login_payload,
    base_user_register_payload,
    valid_host_payload,
    valid_range_deploy_payload,
    valid_range_payload,
    valid_subnet_payload,
    valid_vpc_payload,
)

###### Test /ranges/deploy #######

# global auth token to be used in all tests
auth_token = None
encryption_token = None

user_register_payload = copy.deepcopy(base_user_register_payload)
user_login_payload = copy.deepcopy(base_user_login_payload)

user_register_payload["email"] = "test-ranges@ufsit.club"
user_login_payload["email"] = user_register_payload["email"]


async def test_deploy_without_enc_key(client: AsyncClient) -> None:
    """Test that attempting to deploy a range without being logged in will fail since the encryption key was not given from successful login."""
    response = await client.post(
        f"{BASE_ROUTE}/ranges/deploy", json=valid_range_deploy_payload
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_deploy_without_valid_enc_key(client: AsyncClient) -> None:
    """Test that attempting to deploy a range without an invalid encryption key will fail. This must run before all later tests to provide the global auth and encryption key tokens for the other tests."""
    response = await client.post(
        f"{BASE_ROUTE}/auth/register", json=user_register_payload
    )

    assert response.status_code == status.HTTP_200_OK

    login_response = await client.post(
        f"{BASE_ROUTE}/auth/login", json=user_login_payload
    )
    assert login_response.status_code == status.HTTP_200_OK

    global auth_token  # noqa: PLW0603
    auth_token = login_response.cookies.get("token")
    if not auth_token:
        pytest.fail("Failed to get auth token.")

    global encryption_token  # noqa: PLW0603
    encryption_token = login_response.cookies.get("enc_key")

    modified_enc_key = "in*vali*^%$"
    client.cookies.update({"token": auth_token, "enc_key": modified_enc_key})
    response = await client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=valid_range_deploy_payload,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
