import copy

import yaml
from fastapi import status
from httpx import AsyncClient

from .config import (
    BASE_ROUTE,
    base_user_login_payload,
    base_user_register_payload,
    valid_host_payload,
    valid_range_payload,
    valid_subnet_payload,
    valid_vpc_payload,
)

auth_token = None

user_register_payload = copy.deepcopy(base_user_register_payload)
user_login_payload = copy.deepcopy(base_user_login_payload)

user_register_payload["email"] = "test-middleware@ufsit.club"
user_login_payload["email"] = user_register_payload["email"]


async def test_get_auth_token(client: AsyncClient) -> None:
    """Get the authentication token for the test user. This must run first to provide the global auth token for the other tests."""
    response = await client.post(
        f"{BASE_ROUTE}/auth/register", json=user_register_payload
    )

    assert response.status_code == status.HTTP_200_OK

    login_response = await client.post(
        f"{BASE_ROUTE}/auth/login", json=user_login_payload
    )
    assert login_response.status_code == status.HTTP_200_OK

    global auth_token
    auth_token = login_response.cookies.get("token")


async def test_template_yaml_to_json_range(client: AsyncClient) -> None:
    """Test that YAML payload is correctly converted to JSON for range templates."""
    client.headers.update({"Authorization": f"Bearer {auth_token}"})

    yaml_payload = yaml.dump(valid_range_payload)

    # Post with YAML content type
    response = await client.post(
        f"{BASE_ROUTE}/templates/ranges",
        content=yaml_payload,
        headers={"Content-Type": "application/yaml"},
    )
    assert response.status_code == status.HTTP_200_OK
    range_id = response.json()["id"]

    # Verify the template was correctly stored
    response = await client.get(f"{BASE_ROUTE}/templates/ranges/{range_id}")
    assert response.status_code == status.HTTP_200_OK

    # Expected response with ID
    expected_response = {"id": range_id, **valid_range_payload}
    assert response.json() == expected_response


async def test_template_yaml_to_json_vpc(client: AsyncClient) -> None:
    """Test that YAML payload is correctly converted to JSON for VPC templates."""
    client.headers.update({"Authorization": f"Bearer {auth_token}"})

    yaml_payload = yaml.dump(valid_vpc_payload)

    # Post with YAML content type
    response = await client.post(
        f"{BASE_ROUTE}/templates/vpcs",
        content=yaml_payload,
        headers={"Content-Type": "application/yaml"},
    )
    assert response.status_code == status.HTTP_200_OK
    vpc_id = response.json()["id"]

    # Verify the template was correctly stored
    response = await client.get(f"{BASE_ROUTE}/templates/vpcs/{vpc_id}")
    assert response.status_code == status.HTTP_200_OK

    # Expected response with ID
    expected_response = {"id": vpc_id, **valid_vpc_payload}
    assert response.json() == expected_response


async def test_template_yaml_to_json_subnet(client: AsyncClient) -> None:
    """Test that YAML payload is correctly converted to JSON for subnet templates."""
    client.headers.update({"Authorization": f"Bearer {auth_token}"})

    yaml_payload = yaml.dump(valid_subnet_payload)

    # Post with YAML content type
    response = await client.post(
        f"{BASE_ROUTE}/templates/subnets",
        content=yaml_payload,
        headers={"Content-Type": "application/yaml"},
    )
    assert response.status_code == status.HTTP_200_OK
    subnet_id = response.json()["id"]

    # Verify the template was correctly stored
    response = await client.get(f"{BASE_ROUTE}/templates/subnets/{subnet_id}")
    assert response.status_code == status.HTTP_200_OK

    # Expected response with ID
    expected_response = {"id": subnet_id, **valid_subnet_payload}
    assert response.json() == expected_response


async def test_template_yaml_to_json_host(client: AsyncClient) -> None:
    """Test that YAML payload is correctly converted to JSON for host templates."""
    client.headers.update({"Authorization": f"Bearer {auth_token}"})

    yaml_payload = yaml.dump(valid_host_payload)

    # Post with YAML content type
    response = await client.post(
        f"{BASE_ROUTE}/templates/hosts",
        content=yaml_payload,
        headers={"Content-Type": "application/yaml"},
    )
    assert response.status_code == status.HTTP_200_OK
    host_id = response.json()["id"]

    # Verify the template was correctly stored
    response = await client.get(f"{BASE_ROUTE}/templates/hosts/{host_id}")
    assert response.status_code == status.HTTP_200_OK

    # Expected response with ID
    expected_response = {"id": host_id, **valid_host_payload}
    assert response.json() == expected_response


async def test_template_yaml_to_json_invalid_yaml(client: AsyncClient) -> None:
    """Test that invalid YAML payloads are properly handled with an error."""
    client.headers.update({"Authorization": f"Bearer {auth_token}"})

    # Invalid YAML content (missing colon after field)
    invalid_yaml = """
    name example-range-invalid
    provider: aws
    vpn: false
    vnc: false
    vpcs:
    - name: example-vpc-1
      cidr: 192.168.0.0/16
    """

    # Post with YAML content type
    response = await client.post(
        f"{BASE_ROUTE}/templates/ranges",
        content=invalid_yaml,
        headers={"Content-Type": "application/yaml"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "yaml" in str(response.json()["detail"]).lower()


async def test_yaml_middleware_scoped_properly(client: AsyncClient) -> None:
    """Test that the YAML middleware is properly scoped to the correct routes."""
    yaml_payload = yaml.dump(user_register_payload)
    response = await client.post(
        f"{BASE_ROUTE}/auth/register",
        content=yaml_payload,
        headers={"Content-Type": "application/yaml"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
