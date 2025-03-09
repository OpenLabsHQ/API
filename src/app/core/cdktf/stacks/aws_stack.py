from cdktf_cdktf_provider_aws.eip import Eip
from cdktf_cdktf_provider_aws.instance import Instance
from cdktf_cdktf_provider_aws.internet_gateway import InternetGateway
from cdktf_cdktf_provider_aws.key_pair import KeyPair
from cdktf_cdktf_provider_aws.nat_gateway import NatGateway
from cdktf_cdktf_provider_aws.provider import AwsProvider
from cdktf_cdktf_provider_aws.route import Route
from cdktf_cdktf_provider_aws.route_table import RouteTable
from cdktf_cdktf_provider_aws.route_table_association import RouteTableAssociation
from cdktf_cdktf_provider_aws.security_group import SecurityGroup
from cdktf_cdktf_provider_aws.security_group_rule import SecurityGroupRule
from cdktf_cdktf_provider_aws.subnet import Subnet
from cdktf_cdktf_provider_aws.vpc import Vpc

from ....enums.operating_systems import AWS_OS_MAP
from ....enums.regions import AWS_REGION_MAP, OpenLabsRegion
from ....enums.specs import AWS_SPEC_MAP
from ....schemas.template_range_schema import TemplateRangeSchema
from .base_stack import AbstractBaseStack


class AWSStack(AbstractBaseStack):
    """Stack for generating terraform for AWS."""

    def build_resources(
        self,
        template_range: TemplateRangeSchema,
        region: OpenLabsRegion,
    ) -> None:
        """Initialize AWS terraform stack.

        Args:
        ----
            template_range (TemplateRangeSchema): Template range object to build terraform for.
            region (OpenLabsRegion): Support OpenLabs cloud region.
            secrets (SecretSchema): Cloud secrets.

        Returns:
        -------
            None

        """
        AwsProvider(
            self,
            "AWS",
            region=AWS_REGION_MAP[region],
        )

        # Step 5: Create the key access to all instances provisioned on AWS
        key_pair = KeyPair(
            self,
            "JumpBoxKeyPair",
            key_name="cdktf-key",
            public_key="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIH8URIMqVKb6EAK4O+E+9g8df1uvcOfpvPFl7sQrX7KM email@example.com",  # NOTE: Hardcoded key, will need a way to dynamically add a key to user instances
            tags={"Name": "cdktf-public-key"},
        )

        for vpc in template_range.vpcs:

            # Step 1: Create a VPC
            new_vpc = Vpc(
                self,
                vpc.name,
                cidr_block=str(vpc.cidr),
                enable_dns_support=True,
                enable_dns_hostnames=True,
                tags={"Name": vpc.name},
            )

            # Function to derive a subnet CIDR from the VPC CIDR
            def modify_cidr(vpc_cidr: str, new_third_octet: int) -> str:
                ip_part, prefix = vpc_cidr.split("/")
                octets = ip_part.split(".")
                octets[2] = str(new_third_octet)  # Change the third octet
                octets[3] = "0"  # Explicitly set the fourth octet to 0
                return f"{'.'.join(octets)}/24"  # Convert back to CIDR

            # Generate the new subnet CIDR with third octet = 99
            public_subnet_cidr = modify_cidr(str(vpc.cidr), 99)

            # Step 2: Create a Public Subnet for the Jump Box
            public_subnet = Subnet(
                self,
                f"RangePublicSubnet-{vpc.name}",
                vpc_id=new_vpc.id,
                cidr_block=public_subnet_cidr,
                map_public_ip_on_launch=True,  # Enable public IP auto-assignment
                availability_zone="us-east-1a",
                tags={"Name": f"RangePublicSubnet-{vpc.name}"},
            )

            # Step 3: Create an Internet Gateway for Public Subnet
            igw = InternetGateway(
                self,
                f"RangeInternetGateway-{vpc.name}",
                vpc_id=new_vpc.id,
                tags={"Name": "RangeInternetGateway"},
            )

            # Step 4: Create a NAT Gateway for Private Subnet with EIP
            eip = Eip(
                self, f"RangeNatEIP-{vpc.name}", tags={"Name": "RangeNatEIP"}
            )  # Elastic IP for NAT Gateway
            nat_gateway = NatGateway(
                self,
                f"RangeNatGateway-{vpc.name}",
                subnet_id=public_subnet.id,  # NAT must be in a public subnet
                allocation_id=eip.id,
                tags={"Name": "RangeNatGateway"},
            )

            # Step 6: Create a Route Table for Public Subnet with association
            public_route_table = RouteTable(
                self,
                f"RangePublicRouteTable-{vpc.name}",
                vpc_id=new_vpc.id,
                tags={"Name": "RangePublicRouteTable"},
            )
            Route(
                self,
                f"RangePublicInternetRoute-{vpc.name}",
                route_table_id=public_route_table.id,
                destination_cidr_block="0.0.0.0/0",  # Allow internet access
                gateway_id=igw.id,
            )
            RouteTableAssociation(
                self,
                f"RangePublicRouteAssociation-{vpc.name}",
                subnet_id=public_subnet.id,
                route_table_id=public_route_table.id,
            )

            # Step 7: Create a Route Table for Private Subnet (Using NAT)
            private_route_table = RouteTable(
                self,
                f"RangePrivateRouteTable-{vpc.name}",
                vpc_id=new_vpc.id,
                tags={"Name": "RangePrivateRouteTable"},
            )
            Route(
                self,
                f"RangePrivateNatRoute-{vpc.name}",
                route_table_id=private_route_table.id,
                destination_cidr_block="0.0.0.0/0",  # Allow internet access
                nat_gateway_id=nat_gateway.id,  # Route through NAT Gateway
            )

            # Step 8: Create Security Group and Rules for Jump Box (only allow SSH directly into jump box, for now)
            jumpbox_sg = SecurityGroup(
                self,
                f"RangeJumpBoxSecurityGroup-{vpc.name}",
                vpc_id=new_vpc.id,
                tags={"Name": "RangeJumpBoxSecurityGroup"},
            )
            SecurityGroupRule(
                self,
                f"RangeAllowJumpBoxSSHFromInternet-{vpc.name}",
                type="ingress",
                from_port=22,
                to_port=22,
                protocol="tcp",
                cidr_blocks=["0.0.0.0/0"],  # Allow SSH from anywhere
                security_group_id=jumpbox_sg.id,
            )
            SecurityGroupRule(
                self,
                f"RangeJumpBoxAllowOutbound-{vpc.name}",
                type="egress",
                from_port=0,
                to_port=0,
                protocol="-1",
                cidr_blocks=["0.0.0.0/0"],
                security_group_id=jumpbox_sg.id,
            )

            # Step 9. Dynamically Create Internal Private Subnets from provided list (NOTE: Will eventually create from passed in CyberRange object). First grab all passed in subnet CIDRs to use for making the relevan security group rules
            private_cidrs = [str(subnet.cidr) for subnet in vpc.subnets]

            # Step 10: Create Security Group for Private EC2 Instances
            private_sg = SecurityGroup(
                self,
                f"RangePrivateInternalSecurityGroup-{vpc.name}",
                vpc_id=new_vpc.id,
                tags={"Name": "RangePrivateInternalSecurityGroup"},
            )
            SecurityGroupRule(
                self,
                f"RangeAllowAllTrafficFromJumpBox-{vpc.name}",
                type="ingress",
                from_port=0,
                to_port=0,
                protocol="-1",
                security_group_id=private_sg.id,
                source_security_group_id=jumpbox_sg.id,  # Allow all traffic from Jump Box
            )
            SecurityGroupRule(
                self,
                f"RangeAllowInternalTraffic-{vpc.name}",  # Allow all internal subnets to communicate ONLY with each other
                type="ingress",
                from_port=0,
                to_port=0,
                protocol="-1",
                cidr_blocks=private_cidrs,  # Use dynamically created CIDR blocks
                security_group_id=private_sg.id,
            )
            SecurityGroupRule(
                self,
                f"RangeAllowPrivateOutbound-{vpc.name}",
                type="egress",
                from_port=0,
                to_port=0,
                protocol="-1",
                cidr_blocks=["0.0.0.0/0"],
                security_group_id=private_sg.id,
            )

            # Step 11: Create Jump Box
            Instance(
                self,
                f"JumpBoxInstance-{vpc.name}",
                ami="ami-014f7ab33242ea43c",  # Amazon Ubuntu 20.04 AMI
                instance_type="t2.micro",
                subnet_id=public_subnet.id,
                vpc_security_group_ids=[jumpbox_sg.id],
                associate_public_ip_address=True,  # Ensures public IP is assigned
                key_name=key_pair.key_name,  # Use the generated key pair
                tags={"Name": f"JumpBox-{vpc.name}"},
            )

            # Step 12: Create private subnets with their respecitve EC2 instances
            for subnet in vpc.subnets:
                new_subnet = Subnet(
                    self,
                    f"{subnet.name}-{vpc.name}",
                    vpc_id=new_vpc.id,
                    cidr_block=str(subnet.cidr),
                    availability_zone="us-east-1a",
                    tags={"Name": f"{subnet.name}-{vpc.name}"},
                )
                RouteTableAssociation(
                    self,
                    f"{subnet.name}-RouteAssociation-{vpc.name}",
                    subnet_id=new_subnet.id,
                    route_table_id=private_route_table.id,
                )
                for (
                    host
                ) in subnet.hosts:  # Create specified instances in the given subnet
                    Instance(
                        self,
                        f"{host.hostname}-{vpc.name}",
                        ami=AWS_OS_MAP[
                            host.os
                        ],  # WIll need to grab from update OpenLabsRange object
                        instance_type=AWS_SPEC_MAP[host.spec],
                        subnet_id=new_subnet.id,
                        vpc_security_group_ids=[private_sg.id],
                        key_name=key_pair.key_name,  # Use the generated key pair
                        tags={"Name": f"{host.hostname}-{vpc.name}"},
                    )
