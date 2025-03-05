import copy

from fastapi import status
from httpx import AsyncClient

from .config import BASE_ROUTE

# Test user credentials
user_register_payload = {
    "email": "test-users@ufsit.club",
    "password": "password123",
    "name": "Test User",
}

user_login_payload = copy.deepcopy(user_register_payload)
user_login_payload.pop("name")

# Test data for password update
password_update_payload = {
    "current_password": "password123",
    "new_password": "newpassword123",
}

# Test data for AWS secrets
aws_secrets_payload = {
    "aws_access_key": "AKIAIOSFODNN7EXAMPLE",
    "aws_secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
}

# Test data for Azure secrets
azure_secrets_payload = {
    "azure_client_id": "00000000-0000-0000-0000-000000000000",
    "azure_client_secret": "example-client-secret-value",
}

# Global auth token to be used in all tests
auth_token = None


async def test_get_auth_token(client: AsyncClient) -> None:
    """Get authentication token for the test user.

    This must run first to provide the global auth token for other tests.
    """
    # First register a user
    register_response = await client.post(
        f"{BASE_ROUTE}/auth/register", json=user_register_payload
    )
    assert register_response.status_code == status.HTTP_200_OK

    # Login to get token
    login_response = await client.post(
        f"{BASE_ROUTE}/auth/login", json=user_login_payload
    )
    assert login_response.status_code == status.HTTP_200_OK
    assert "token" in login_response.cookies

    # Set global auth token
    global auth_token
    auth_token = login_response.cookies.get("token")


async def test_get_user_info(client: AsyncClient) -> None:
    """Test retrieving the current user's information."""
    # Set the authorization header with the token
    client.headers.update({"Authorization": f"Bearer {auth_token}"})

    # Get user info
    response = await client.get(f"{BASE_ROUTE}/users/me")
    assert response.status_code == status.HTTP_200_OK

    # Verify the response contains the expected user information
    user_info = response.json()
    assert user_info["email"] == user_register_payload["email"]
    assert user_info["name"] == user_register_payload["name"]


async def test_update_password_flow(client: AsyncClient) -> None:
    """Test the complete password update flow."""
    # Set the authorization header with the token
    client.headers.update({"Authorization": f"Bearer {auth_token}"})

    # Update password
    update_response = await client.post(
        f"{BASE_ROUTE}/users/me/password", json=password_update_payload
    )
    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.json()["message"] == "Password updated successfully"

    # Try to login with new password
    new_login_payload = copy.deepcopy(user_login_payload)
    new_login_payload["password"] = password_update_payload["new_password"]

    new_login_response = await client.post(
        f"{BASE_ROUTE}/auth/login", json=new_login_payload
    )
    assert new_login_response.status_code == status.HTTP_200_OK

    # Get the new token
    new_token = new_login_response.cookies.get("token")

    # Reset password back for other tests
    reset_payload = {
        "current_password": password_update_payload["new_password"],
        "new_password": password_update_payload["current_password"],
    }

    # Use the new token to reset the password
    client.headers.update({"Authorization": f"Bearer {new_token}"})
    reset_response = await client.post(
        f"{BASE_ROUTE}/users/me/password", json=reset_payload
    )
    assert reset_response.status_code == status.HTTP_200_OK

    # Restore the global token after test is done
    client.headers.update({"Authorization": f"Bearer {auth_token}"})


async def test_update_password_with_incorrect_current(client: AsyncClient) -> None:
    """Test password update with incorrect current password."""
    # Set the authorization header with the token
    client.headers.update({"Authorization": f"Bearer {auth_token}"})

    # Try update with wrong current password
    invalid_payload = copy.deepcopy(password_update_payload)
    # Using an incorrect password to test validation - not a security risk
    invalid_payload["current_password"] = "incorrect-password-for-testing"  # noqa: S105

    update_response = await client.post(
        f"{BASE_ROUTE}/users/me/password", json=invalid_payload
    )
    assert update_response.status_code == status.HTTP_400_BAD_REQUEST
    assert update_response.json()["detail"] == "Current password is incorrect"


async def test_secrets_operations(client: AsyncClient) -> None:
    """Test all secret-related operations."""
    # Set the authorization header with the token
    client.headers.update({"Authorization": f"Bearer {auth_token}"})

    # Check initial secrets status
    status_response = await client.get(f"{BASE_ROUTE}/users/me/secrets")
    assert status_response.status_code == status.HTTP_200_OK

    # Check the status response is valid JSON
    # (not asserting specific values as test order may vary)
    _ = status_response.json()

    # Add AWS credentials
    aws_response = await client.post(
        f"{BASE_ROUTE}/users/me/secrets/aws", json=aws_secrets_payload
    )
    assert aws_response.status_code == status.HTTP_200_OK
    assert aws_response.json()["message"] == "AWS credentials updated successfully"

    # Check updated status
    updated_status_response = await client.get(f"{BASE_ROUTE}/users/me/secrets")
    assert updated_status_response.status_code == status.HTTP_200_OK

    aws_status = updated_status_response.json()
    assert aws_status["aws"]["has_credentials"] is True
    assert "created_at" in aws_status["aws"]

    # Add Azure credentials
    azure_response = await client.post(
        f"{BASE_ROUTE}/users/me/secrets/azure", json=azure_secrets_payload
    )
    assert azure_response.status_code == status.HTTP_200_OK
    assert azure_response.json()["message"] == "Azure credentials updated successfully"

    # Final status check
    final_status_response = await client.get(f"{BASE_ROUTE}/users/me/secrets")
    assert final_status_response.status_code == status.HTTP_200_OK

    final_status = final_status_response.json()
    assert final_status["aws"]["has_credentials"] is True
    assert final_status["azure"]["has_credentials"] is True
    assert "created_at" in final_status["azure"]


async def test_unauthenticated_access(client: AsyncClient) -> None:
    """Test that unauthenticated users cannot access protected endpoints."""
    # Clear any authorization headers
    client.headers.clear()

    # Try to access user info without authentication
    response = await client.get(f"{BASE_ROUTE}/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Try to update password without authentication
    response = await client.post(
        f"{BASE_ROUTE}/users/me/password", json=password_update_payload
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Try to get secrets status without authentication
    response = await client.get(f"{BASE_ROUTE}/users/me/secrets")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Try to update AWS secrets without authentication
    response = await client.post(
        f"{BASE_ROUTE}/users/me/secrets/aws", json=aws_secrets_payload
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Try to update Azure secrets without authentication
    response = await client.post(
        f"{BASE_ROUTE}/users/me/secrets/azure", json=azure_secrets_payload
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
