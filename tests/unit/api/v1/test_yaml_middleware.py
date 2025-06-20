import yaml
from fastapi import status
from httpx import AsyncClient

from .config import (
    BASE_ROUTE,
    valid_host_payload,
    valid_range_payload,
    valid_subnet_payload,
    valid_vpc_payload,
)


async def test_template_yaml_to_json_range(auth_client: AsyncClient) -> None:
    """Test that YAML payload is correctly converted to JSON for range templates."""
    yaml_payload = yaml.dump(valid_range_payload)

    # Post with YAML content type
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges",
        content=yaml_payload,
        headers={"Content-Type": "application/yaml"},
    )
    assert response.status_code == status.HTTP_200_OK
    range_id = response.json()["id"]

    # Verify the template was correctly stored
    response = await auth_client.get(f"{BASE_ROUTE}/templates/ranges/{range_id}")
    assert response.status_code == status.HTTP_200_OK

    # Expected response with ID
    expected_response = {"id": range_id, **valid_range_payload}
    assert response.json() == expected_response


async def test_template_yaml_to_json_vpc(auth_client: AsyncClient) -> None:
    """Test that YAML payload is correctly converted to JSON for VPC templates."""
    yaml_payload = yaml.dump(valid_vpc_payload)

    # Post with YAML content type
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/vpcs",
        content=yaml_payload,
        headers={"Content-Type": "application/yaml"},
    )
    assert response.status_code == status.HTTP_200_OK
    vpc_id = response.json()["id"]

    # Verify the template was correctly stored
    response = await auth_client.get(f"{BASE_ROUTE}/templates/vpcs/{vpc_id}")
    assert response.status_code == status.HTTP_200_OK

    # Expected response with ID
    expected_response = {"id": vpc_id, **valid_vpc_payload}
    assert response.json() == expected_response


async def test_template_yaml_to_json_subnet(auth_client: AsyncClient) -> None:
    """Test that YAML payload is correctly converted to JSON for subnet templates."""
    yaml_payload = yaml.dump(valid_subnet_payload)

    # Post with YAML content type
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/subnets",
        content=yaml_payload,
        headers={"Content-Type": "application/yaml"},
    )
    assert response.status_code == status.HTTP_200_OK
    subnet_id = response.json()["id"]

    # Verify the template was correctly stored
    response = await auth_client.get(f"{BASE_ROUTE}/templates/subnets/{subnet_id}")
    assert response.status_code == status.HTTP_200_OK

    # Expected response with ID
    expected_response = {"id": subnet_id, **valid_subnet_payload}
    assert response.json() == expected_response


async def test_template_yaml_to_json_host(auth_client: AsyncClient) -> None:
    """Test that YAML payload is correctly converted to JSON for host templates."""
    yaml_payload = yaml.dump(valid_host_payload)

    # Post with YAML content type
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/hosts",
        content=yaml_payload,
        headers={"Content-Type": "application/yaml"},
    )
    assert response.status_code == status.HTTP_200_OK
    host_id = response.json()["id"]

    # Verify the template was correctly stored
    response = await auth_client.get(f"{BASE_ROUTE}/templates/hosts/{host_id}")
    assert response.status_code == status.HTTP_200_OK

    # Expected response with ID
    expected_response = {"id": host_id, **valid_host_payload}
    assert response.json() == expected_response


async def test_template_yaml_to_json_invalid_yaml(auth_client: AsyncClient) -> None:
    """Test that invalid YAML payloads are properly handled with an error."""
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
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges",
        content=invalid_yaml,
        headers={"Content-Type": "application/yaml"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "yaml" in str(response.json()["detail"]).lower()


async def test_yaml_middleware_scoped_properly(client: AsyncClient) -> None:
    """Test that the YAML middleware is properly scoped to the correct routes."""
    # Create a minimal user payload
    user_payload = {
        "email": "test-yaml-scope@example.com",
        "password": "testPassword123!",
        "name": "Test User",
    }
    yaml_payload = yaml.dump(user_payload)
    response = await client.post(
        f"{BASE_ROUTE}/auth/register",
        content=yaml_payload,
        headers={"Content-Type": "application/yaml"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_tag_propagation(auth_client: AsyncClient) -> None:
    """Test that tags are processed but the test verifies request conversion not database storage."""
    # Create a payload with minimal required attributes but with tags at all levels
    range_with_tags = {
        "name": "tags-test-range",
        "provider": "aws",
        "vnc": False,
        "vpn": False,
        "tags": ["range-tag"],
        "vpcs": [
            {
                "name": "tags-test-vpc",
                "cidr": "10.0.0.0/16",
                "tags": ["vpc-tag"],
                "subnets": [
                    {
                        "name": "tags-test-subnet",
                        "cidr": "10.0.1.0/24",
                        "tags": ["subnet-tag"],
                        "hosts": [
                            {
                                "hostname": "tags-test-host",
                                "os": "debian_11",
                                "spec": "tiny",
                                "size": 8,
                                "tags": ["host-tag"],
                            }
                        ],
                    }
                ],
            }
        ],
    }

    yaml_payload = yaml.dump(range_with_tags)

    # Post with YAML content type
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges",
        content=yaml_payload,
        headers={"Content-Type": "application/yaml"},
    )
    assert response.status_code == status.HTTP_200_OK
    range_id = response.json()["id"]

    # Verify the template was correctly stored
    response = await auth_client.get(f"{BASE_ROUTE}/templates/ranges/{range_id}")
    assert response.status_code == status.HTTP_200_OK

    # Expected tags
    assert set(response.json()["vpcs"][0]["subnets"][0]["hosts"][0]["tags"]) == {
        "host-tag",
        "subnet-tag",
        "vpc-tag",
        "range-tag",
    }
