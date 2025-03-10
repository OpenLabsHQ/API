import copy
from typing import Any
import uuid
from src.app.enums.regions import OpenLabsRegion

# Base route
BASE_ROUTE = "/api/v1"


# ==============================
#       Template Payloads
# ==============================

# Valid payload for comparison
valid_range_payload: dict[str, Any] = {
    "vpcs": [
        {
            "cidr": "192.168.0.0/16",
            "name": "example-vpc-1",
            "subnets": [
                {
                    "cidr": "192.168.1.0/24",
                    "name": "example-subnet-1",
                    "hosts": [
                        {
                            "hostname": "example-host-1",
                            "os": "debian_11",
                            "spec": "tiny",
                            "size": 8,
                            "tags": ["web", "linux"],
                        }
                    ],
                }
            ],
        }
    ],
    "provider": "aws",
    "name": "example-range-1",
    "vnc": False,
    "vpn": False,
}

# Valid range payload for deployment
valid_range_deploy_payload: dict[str, Any] = {
    "name": "test-deploy-range-1",
    "description": "test range to deploy",
    "template_id": str(uuid.uuid4()),
    "region": OpenLabsRegion.US_EAST_1.value,
    "readme": "",
}

valid_vpc_payload = copy.deepcopy(valid_range_payload["vpcs"][0])
valid_subnet_payload = copy.deepcopy(valid_vpc_payload["subnets"][0])
valid_host_payload = copy.deepcopy(valid_subnet_payload["hosts"][0])

# ==============================
#      User/Auth Payloads
# ==============================

# Test user credentials
base_user_register_payload = {
    "email": "test@ufsit.club",
    "password": "password123",
    "name": "Test User",
}

base_user_login_payload = copy.deepcopy(base_user_register_payload)
base_user_login_payload.pop("name")

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
    "azure_tenant_id": "00000000-0000-0000-0000-000000000000",
    "azure_subscription_id": "00000000-0000-0000-0000-000000000000",
}
