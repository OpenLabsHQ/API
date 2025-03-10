from typing import Any

from src.app.schemas.template_range_schema import TemplateRangeSchema


# Function to derive a subnet CIDR from the VPC CIDR
def modify_cidr(vpc_cidr: str, new_third_octet: int) -> str:
    """Dervies public subnet with third octet = 99 from the vpc cidr block."""
    ip_part, prefix = vpc_cidr.split("/")
    octets = ip_part.split(".")
    octets[2] = str(new_third_octet)  # Change the third octet
    octets[3] = "0"  # Explicitly set the fourth octet to 0
    return f"{'.'.join(octets)}/24"  # Convert back to CIDR


# Valid payload for comparison
one_all_template_dict: dict[str, Any] = {
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
        },
        {
            "cidr": "10.10.0.0/16",
            "name": "example-vpc-2",
            "subnets": [
                {
                    "cidr": "10.10.1.0/24",
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
        },
    ],
    "provider": "aws",
    "name": "example-range-2",
    "vnc": False,
    "vpn": False,
}

one_all_template = TemplateRangeSchema.model_validate(
    one_all_template_dict, from_attributes=True
)
