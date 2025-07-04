import copy
import random
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.cdktf.ranges.base_range import AbstractBaseRange
from src.app.core.cdktf.ranges.range_factory import RangeFactory
from src.app.enums.regions import OpenLabsRegion
from src.app.models.user_model import UserModel
from src.app.schemas.range_schemas import (
    DeployedRangeHeaderSchema,
    DeployedRangeKeySchema,
    DeployedRangeSchema,
)
from src.app.schemas.secret_schema import SecretSchema
from tests.api_test_utils import authenticate_client

from .config import (
    BASE_ROUTE,
    valid_blueprint_range_create_payload,
    valid_deployed_range_data,
    valid_range_deploy_payload,
    valid_range_private_key_data,
)

pytestmark = pytest.mark.unit


async def test_deploy_without_valid_secrets(
    auth_client: AsyncClient, mock_decrypt_no_secrets: None
) -> None:
    """Test that attempting to deploy a range without valid cloud provider credentials will fail (no secrets in database for user)."""
    enc_key = "VGhpcyBpcyBhIHRlc3Qgc3RyaW5nIGZvciBiYXNlNjQgZW5jb2Rpbmcu"
    auth_client.cookies.update({"enc_key": enc_key})
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges",
        json=valid_blueprint_range_create_payload,
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_id = int(response.json()["id"])

    blueprint_deploy_payload = copy.deepcopy(valid_range_deploy_payload)
    blueprint_deploy_payload["blueprint_id"] = blueprint_id

    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=blueprint_deploy_payload,
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_deploy_range_synthesize_failure(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_synthesize_failure: None,
) -> None:
    """Test to deploy a range but fail during the systhesize step."""
    enc_key = "VGhpcyBpcyBhIHRlc3Qgc3RyaW5nIGZvciBiYXNlNjQgZW5jb2Rpbmcu"
    auth_client.cookies.update({"enc_key": enc_key})
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges",
        json=valid_blueprint_range_create_payload,
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_id = int(response.json()["id"])

    blueprint_deploy_payload = copy.deepcopy(valid_range_deploy_payload)
    blueprint_deploy_payload["blueprint_id"] = blueprint_id

    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=blueprint_deploy_payload,
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


async def test_deploy_range_deploy_failure(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_deploy_failure: None,
) -> None:
    """Test to deploy a range but fail during the deploy step."""
    enc_key = "VGhpcyBpcyBhIHRlc3Qgc3RyaW5nIGZvciBiYXNlNjQgZW5jb2Rpbmcu"
    auth_client.cookies.update({"enc_key": enc_key})
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges",
        json=valid_blueprint_range_create_payload,
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_id = int(response.json()["id"])

    blueprint_deploy_payload = copy.deepcopy(valid_range_deploy_payload)
    blueprint_deploy_payload["blueprint_id"] = blueprint_id

    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=blueprint_deploy_payload,
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


async def test_deploy_range_database_failure(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_deploy_success: None,
    mock_create_range_in_db_failure: None,
) -> None:
    """Test to deploy a range but fail when adding the deployed range model to the database."""
    enc_key = "VGhpcyBpcyBhIHRlc3Qgc3RyaW5nIGZvciBiYXNlNjQgZW5jb2Rpbmcu"
    auth_client.cookies.update({"enc_key": enc_key})
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges",
        json=valid_blueprint_range_create_payload,
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_id = int(response.json()["id"])

    blueprint_deploy_payload = copy.deepcopy(valid_range_deploy_payload)
    blueprint_deploy_payload["blueprint_id"] = blueprint_id

    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=blueprint_deploy_payload,
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


async def test_deploy_range_deploy_success(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_deploy_success: None,
    mock_create_range_in_db_success: None,
) -> None:
    """Test to deploy a range successfully with a returned range ID."""
    enc_key = "VGhpcyBpcyBhIHRlc3Qgc3RyaW5nIGZvciBiYXNlNjQgZW5jb2Rpbmcu"
    auth_client.cookies.update({"enc_key": enc_key})
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges",
        json=valid_blueprint_range_create_payload,
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_id = int(response.json()["id"])

    blueprint_deploy_payload = copy.deepcopy(valid_range_deploy_payload)
    blueprint_deploy_payload["blueprint_id"] = blueprint_id

    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=blueprint_deploy_payload,
    )
    assert response.status_code == status.HTTP_200_OK
    assert int(response.json()["id"])


async def test_destroy_without_valid_range_owner(
    auth_client: AsyncClient,
    client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_deploy_success: None,
    mock_create_range_in_db_success: None,
) -> None:
    """Test that attempting to destroy a range that a user does not own will fail."""
    # User 1
    enc_key = "VGhpcyBpcyBhIHRlc3Qgc3RyaW5nIGZvciBiYXNlNjQgZW5jb2Rpbmcu"
    auth_client.cookies.update({"enc_key": enc_key})
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges",
        json=valid_blueprint_range_create_payload,
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_id = int(response.json()["id"])

    blueprint_deploy_payload = copy.deepcopy(valid_range_deploy_payload)
    blueprint_deploy_payload["blueprint_id"] = blueprint_id

    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=blueprint_deploy_payload,
    )
    assert response.status_code == status.HTTP_200_OK
    user1_range_id = int(response.json()["id"])

    # User 2
    auth_success = await authenticate_client(client)
    if not auth_success:
        pytest.fail("Failed to authenticate client to API!")
    response = await client.delete(f"{BASE_ROUTE}/ranges/{user1_range_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_destroy_decrypt_secrets_failure(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_retrieve_deployed_range_success: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that attempting to destroy a range without valid private key will fail."""

    async def mock_get_decrypted_secrets_false(
        user: UserModel, db: AsyncSession, master_key: bytes
    ) -> None:
        return None

    # Patch the function so that the deploy works, but the destroy fails
    monkeypatch.setattr(
        "src.app.api.v1.ranges.get_decrypted_secrets", mock_get_decrypted_secrets_false
    )

    response = await auth_client.delete(
        f"{BASE_ROUTE}/ranges/{random.randint(-420, -69)}"  # noqa: S311
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


async def test_destroy_without_valid_secrets(
    auth_client: AsyncClient,
    mock_retrieve_deployed_range_success: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that attempting to destroy a range without valid cloud provider credentials will fail (no secrets in database for user)."""

    async def mock_get_decrypted_secrets(
        user: UserModel, db: AsyncSession, master_key: bytes
    ) -> SecretSchema:
        return SecretSchema(
            aws_access_key=None,
            aws_secret_key=None,
            aws_created_at=None,
            azure_client_id=None,
            azure_client_secret=None,
            azure_tenant_id=None,
            azure_subscription_id=None,
            azure_created_at=None,
        )

    # Patch the function so that the deploy works, but the destroy fails
    monkeypatch.setattr(
        "src.app.api.v1.ranges.get_decrypted_secrets", mock_get_decrypted_secrets
    )

    response = await auth_client.delete(
        f"{BASE_ROUTE}/ranges/{random.randint(-420, -69)}"  # noqa: S311
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_destroy_range_synthesize_failure(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_retrieve_deployed_range_success: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test to destroy a range but fail during the systhesize step."""
    deployed_schema = DeployedRangeSchema.model_validate(
        valid_deployed_range_data, from_attributes=True
    )
    monkeypatch.setattr(
        RangeFactory,
        "create_range",
        lambda *args, **kwargs: type(
            "MockRange",
            (AbstractBaseRange,),
            {
                "get_provider_stack_class": lambda self: None,
                "has_secrets": lambda self: True,
                "get_cred_env_vars": lambda self: {},
                "synthesize": lambda self: False,
            },
        )(
            "test-range",
            deployed_schema,
            OpenLabsRegion.US_EAST_1,
            SecretSchema(),
            "Test range description.",
            None,  # No state file
        ),
    )

    response = await auth_client.delete(
        f"{BASE_ROUTE}/ranges/{valid_deployed_range_data["id"]}"
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


async def test_destroy_range_destroy_failure(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_retrieve_deployed_range_success: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test to destroy a range but fail during the destroy step."""
    deployed_schema = DeployedRangeSchema.model_validate(
        valid_deployed_range_data, from_attributes=True
    )
    monkeypatch.setattr(
        RangeFactory,
        "create_range",
        lambda *args, **kwargs: type(
            "MockRange",
            (AbstractBaseRange,),
            {
                "get_provider_stack_class": lambda self: None,
                "has_secrets": lambda self: True,
                "get_cred_env_vars": lambda self: {},
                "synthesize": lambda self: True,
                "destroy": lambda self: False,
            },
        )(
            "test-range",
            deployed_schema,
            OpenLabsRegion.US_EAST_1,
            SecretSchema(),
            "This is a test range description.",
            None,  # No state file
        ),
    )

    response = await auth_client.delete(
        f"{BASE_ROUTE}/ranges/{valid_deployed_range_data["id"]}"
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


async def test_destroy_range_database_failure(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_retrieve_deployed_range_success: None,
    mock_delete_range_in_db_failure: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test to destroy a range but fail when deleting the deployed range model from the database."""
    deployed_schema = DeployedRangeSchema.model_validate(
        valid_deployed_range_data, from_attributes=True
    )
    monkeypatch.setattr(
        RangeFactory,
        "create_range",
        lambda *args, **kwargs: type(
            "MockRange",
            (AbstractBaseRange,),
            {
                "get_provider_stack_class": lambda self: None,
                "has_secrets": lambda self: True,
                "get_cred_env_vars": lambda self: {},
                "synthesize": lambda self: True,
                "destroy": lambda self: True,
            },
        )(
            "test-range",
            deployed_schema,
            OpenLabsRegion.US_EAST_1,
            SecretSchema(),
            "This is a test range description.",
            None,  # No state file
        ),
    )

    response = await auth_client.delete(
        f"{BASE_ROUTE}/ranges/{valid_deployed_range_data["id"]}"
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


async def test_destroy_range_destroy_success(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_retrieve_deployed_range_success: None,
    mock_delete_range_in_db_success: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test to destroy a range successfully with a returned true boolean value."""
    deployed_schema = DeployedRangeSchema.model_validate(
        valid_deployed_range_data, from_attributes=True
    )
    monkeypatch.setattr(
        RangeFactory,
        "create_range",
        lambda *args, **kwargs: type(
            "MockRange",
            (AbstractBaseRange,),
            {
                "get_provider_stack_class": lambda self: None,
                "has_secrets": lambda self: True,
                "get_cred_env_vars": lambda self: {},
                "synthesize": lambda self: True,
                "destroy": lambda self: True,
            },
        )(
            "test-range",
            deployed_schema,
            OpenLabsRegion.US_EAST_1,
            SecretSchema(),
            "This is a test range description.",
            None,  # No state file
        ),
    )

    response = await auth_client.delete(
        f"{BASE_ROUTE}/ranges/{valid_deployed_range_data["id"]}"
    )
    assert response.status_code == status.HTTP_200_OK


async def test_get_range_headers_success(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that we get a 200 response when there is at least one range header found."""
    header = DeployedRangeHeaderSchema.model_validate(valid_deployed_range_data)

    monkeypatch.setattr(
        "src.app.api.v1.ranges.get_deployed_range_headers",
        AsyncMock(return_value=[header]),
    )

    response = await auth_client.get(f"{BASE_ROUTE}/ranges")
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data == [header.model_dump(mode="json")]


async def test_get_range_details_success(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that we get a 200 response when the range we request exists."""
    test_range = DeployedRangeSchema.model_validate(valid_deployed_range_data)

    monkeypatch.setattr(
        "src.app.api.v1.ranges.get_deployed_range",
        AsyncMock(return_value=test_range),
    )

    response = await auth_client.get(f"{BASE_ROUTE}/ranges/1337")
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data == test_range.model_dump(mode="json")


async def test_get_range_key_success(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that we get 200 response when we request the private key for an existing range."""
    test_key = DeployedRangeKeySchema.model_validate(valid_range_private_key_data)

    monkeypatch.setattr(
        "src.app.api.v1.ranges.get_deployed_range_key",
        AsyncMock(return_value=test_key),
    )

    response = await auth_client.get(f"{BASE_ROUTE}/ranges/1337/key")
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data == test_key.model_dump(mode="json")
