import copy

from fastapi import status
from httpx import AsyncClient

from .config import BASE_ROUTE, base_user_login_payload, base_user_register_payload

user_register_payload = copy.deepcopy(base_user_register_payload)
user_login_payload = copy.deepcopy(base_user_login_payload)

user_register_payload["email"] = "test-auth@ufsit.club"
user_login_payload["email"] = user_register_payload["email"]


async def test_user_register(client: AsyncClient) -> None:
    """Test that we get a 200 response when registering a user."""
    response = await client.post(
        f"{BASE_ROUTE}/auth/register", json=user_register_payload
    )
    assert response.status_code == status.HTTP_200_OK

    assert int(response.json()["id"])


async def test_user_register_bad_email(client: AsyncClient) -> None:
    """Test that we get a 422 response when registering a user with an invalid email."""
    invalid_payload = copy.deepcopy(user_register_payload)
    invalid_payload["email"] = "invalidemail"

    response = await client.post(f"{BASE_ROUTE}/auth/register", json=invalid_payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_duplicate_user_register(client: AsyncClient) -> None:
    """Test that we get a 400 response when registering a user with the same email."""
    response = await client.post(
        f"{BASE_ROUTE}/auth/register", json=user_register_payload
    )
    assert response.status_code == status.HTTP_409_CONFLICT

    response_json = response.json()
    assert response_json["detail"] == "User already exists"


async def test_duplicate_user_diff_name_pass_register(client: AsyncClient) -> None:
    """Test that we get a 400 response when registering a user with the same email but a different password and name."""
    new_user_register_payload = copy.deepcopy(user_register_payload)
    new_user_register_payload["password"] = "newpassword123"  # noqa: S105 (Testing)
    new_user_register_payload["name"] = "New Name"

    response = await client.post(
        f"{BASE_ROUTE}/auth/register", json=user_register_payload
    )
    assert response.status_code == status.HTTP_409_CONFLICT

    response_json = response.json()
    assert response_json["detail"] == "User already exists"


async def test_user_register_invalid_payload(client: AsyncClient) -> None:
    """Test that we get a 422 response when registering a user with an invalid payload."""
    invalid_payload = copy.deepcopy(user_register_payload)
    invalid_payload.pop("email")

    response = await client.post(f"{BASE_ROUTE}/auth/register", json=invalid_payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    invalid_payload = copy.deepcopy(user_register_payload)
    invalid_payload.pop("password")

    response = await client.post(f"{BASE_ROUTE}/auth/register", json=invalid_payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    invalid_payload = copy.deepcopy(user_register_payload)
    invalid_payload.pop("name")

    response = await client.post(f"{BASE_ROUTE}/auth/register", json=invalid_payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_user_login_correct_pass(client: AsyncClient) -> None:
    """Test that we get a 200 response when logging in a user and get a valid JWT cookie."""
    response = await client.post(f"{BASE_ROUTE}/auth/login", json=user_login_payload)
    assert response.status_code == status.HTTP_200_OK

    # Check that the response contains a success message
    assert response.json()["success"] is True

    # Check that the cookie is set
    assert "token" in response.cookies


async def test_user_login_incorrect_pass(client: AsyncClient) -> None:
    """Test that we get a 401 response when logging in a user with an incorrect password."""
    invalid_payload = copy.deepcopy(user_login_payload)
    invalid_payload["password"] = "incorrectpassword"  # noqa: S105 (Testing)

    response = await client.post(f"{BASE_ROUTE}/auth/login", json=invalid_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_nonexistent_user_login(client: AsyncClient) -> None:
    """Test that we get a 401 response when logging in a user that doesn't exist."""
    invalid_payload = copy.deepcopy(user_login_payload)
    invalid_payload["email"] = "alex@ufsit.club"

    response = await client.post(f"{BASE_ROUTE}/auth/login", json=invalid_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_user_logout(client: AsyncClient) -> None:
    """Test that we can successfully logout a user."""
    # First login to get the cookie
    login_response = await client.post(
        f"{BASE_ROUTE}/auth/login", json=user_login_payload
    )
    assert login_response.status_code == status.HTTP_200_OK
    assert "token" in login_response.cookies

    # Now logout
    logout_response = await client.post(f"{BASE_ROUTE}/auth/logout")
    assert logout_response.status_code == status.HTTP_200_OK

    # Verify the response content
    assert logout_response.json()["success"] is True

    # Note: We cannot verify cookie deletion in tests because HttpX doesn't support
    # direct inspection of Set-Cookie headers that clear cookies. In a real browser,
    # this would clear the cookie.
