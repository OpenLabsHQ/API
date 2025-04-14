from ipaddress import IPv4Network

from cdktf import TerraformOutput
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
from cdktf_cdktf_provider_aws.ec2_transit_gateway import Ec2TransitGateway
from cdktf_cdktf_provider_aws.ec2_transit_gateway_vpc_attachment import Ec2TransitGatewayVpcAttachment
from cdktf_cdktf_provider_aws.ec2_transit_gateway_route import Ec2TransitGatewayRoute
from cdktf_cdktf_provider_aws.ec2_transit_gateway_route_table import Ec2TransitGatewayRouteTable

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
        cdktf_id: str,
        range_name: str,
    ) -> None:
        """Initialize AWS terraform stack.

        Args:
        ----
            template_range (TemplateRangeSchema): Template range object to build terraform for.
            region (OpenLabsRegion): Support OpenLabs cloud region.
            cdktf_id (str): Unique ID for each deployment to use for Terraform resource naming.
            range_name (str): Name of range to deploy.

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
            f"{range_name}-JumpBoxKeyPair",
            key_name=f"{range_name}-cdktf-key",
            public_key="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIH8URIMqVKb6EAK4O+E+9g8df1uvcOfpvPFl7sQrX7KM email@example.com",  # NOTE: Hardcoded key, will need a way to dynamically add a key to user instances
            tags={"Name": "cdktf-public-key"},
        )

        jumpbox_vpc = Vpc(
            self,
            f"{range_name}-JumpBoxVPC",
            cidr_block="10.255.0.0/16",  # TODO: Dynamically create a cidr block that does not exist with any of the vpc cidr blocks in the template
            enable_dns_support=True,
            enable_dns_hostnames=True,
            tags={"Name": "JumpBoxVPC"},
        )

        # # Function to derive a subnet CIDR from the VPC CIDR
        # def modify_cidr(vpc_cidr: str, new_third_octet: int) -> str:
        #     ip_part, prefix = vpc_cidr.split("/")
        #     octets = ip_part.split(".")
        #     octets[2] = str(new_third_octet)  # Change the third octet
        #     octets[3] = "0"  # Explicitly set the fourth octet to 0
        #     return f"{'.'.join(octets)}/24"  # Convert back to CIDR

        # # Generate the new subnet CIDR with third octet = 99
        # public_subnet_cidr = modify_cidr(str(jumpbox_vpc.cidr_block), 99)

        public_subnet = Subnet(
            self,
            f"{range_name}-JumpBoxPublicSubnet",
            vpc_id=jumpbox_vpc.id,
            cidr_block="10.255.99.0/24",
            availability_zone="us-east-1a",
            map_public_ip_on_launch=True,
            tags={"Name": "JumpBoxPublicSubnet"},
        )

        # Step 3: Create an Internet Gateway for Public Subnet
        igw = InternetGateway(
            self,
            f"{range_name}-RangeInternetGateway",
            vpc_id=jumpbox_vpc.id,
            tags={"Name": "RangeInternetGateway"},
        )

        # Step 4: Create a NAT Gateway for internal network with EIP
        # Elastic IP for NAT Gateway
        eip = Eip(self, f"{range_name}-RangeNatEIP", tags={"Name": "RangeNatEIP"})

        nat_gateway = NatGateway(
            self,
            f"{range_name}-RangeNatGateway",
            subnet_id=public_subnet.id,  # NAT must be in a public subnet
            allocation_id=eip.id,
            tags={"Name": "RangeNatGateway"},
        )

        jumpbox_route_table = RouteTable(
            self,
            f"{range_name}-JumpBoxRouteTable",
            vpc_id=jumpbox_vpc.id,
            tags={"Name": "RangePublicRouteTable"},
        )

        igw_route = Route(
            self,
            f"{range_name}-RangePublicInternetRoute",
            route_table_id=jumpbox_route_table.id,
            destination_cidr_block="0.0.0.0/0",  # Allow internet access
            gateway_id=igw.id,
        )

        public_rt_assoc = RouteTableAssociation(
            self,
            f"{range_name}-RangePublicRouteAssociation",
            subnet_id=public_subnet.id,
            route_table_id=jumpbox_route_table.id,
        )

        # Step 8: Create Security Group and Rules for Jump Box (only allow SSH directly into jump box, for now)
        jumpbox_sg = SecurityGroup(
            self,
            f"{range_name}-RangeJumpBoxSecurityGroup",
            vpc_id=jumpbox_vpc.id,
            tags={"Name": "RangeJumpBoxSecurityGroup"},
        )
        SecurityGroupRule(
            self,
            f"{range_name}-RangeAllowJumpBoxSSHFromInternet",
            type="ingress",
            from_port=22,
            to_port=22,
            protocol="tcp",
            cidr_blocks=["0.0.0.0/0"],  # Allow SSH from anywhere
            security_group_id=jumpbox_sg.id,
        )
        SecurityGroupRule(
            self,
            f"{range_name}-RangeJumpBoxAllowOutbound",
            type="egress",
            from_port=0,
            to_port=0,
            protocol="-1",
            cidr_blocks=["0.0.0.0/0"],
            security_group_id=jumpbox_sg.id,
        )

        # Step 11: Create Jump Box
        jumpbox = Instance(
            self,
            f"{range_name}-JumpBoxInstance",
            ami="ami-014f7ab33242ea43c",  # Amazon Ubuntu 20.04 AMI
            instance_type="t2.micro",
            subnet_id=public_subnet.id,
            vpc_security_group_ids=[jumpbox_sg.id],
            associate_public_ip_address=True,  # Ensures public IP is assigned
            key_name=key_pair.key_name,  # Use the generated key pair
            tags={"Name": f"{range_name}-JumpBox"},
        )

        public_vpc_private_subnet = Subnet(
            self,
            f"{range_name}-JumpBoxVPCPrivateSubnet",
            vpc_id=jumpbox_vpc.id,
            cidr_block="10.255.98.0/24",
            availability_zone="us-east-1a",
            map_public_ip_on_launch=False,
            tags={"Name": "JumpBoxPublicSubnet"},
        )

        # Step 7: Create a Route Table for internal network (Using NAT)
        nat_route_table = RouteTable(
            self,
            f"{range_name}-RangePrivateRouteTable",
            vpc_id=jumpbox_vpc.id,
            tags={"Name": "RangePrivateRouteTable"},
        )
        nat_route = Route(
            self,
            f"{range_name}-RangePrivateNatRoute",
            route_table_id=nat_route_table.id,
            destination_cidr_block="0.0.0.0/0",  # Allow internet access
            nat_gateway_id=nat_gateway.id,  # Route through NAT Gateway
        )
        private_rt_assoc = RouteTableAssociation(
            self,
            f"{range_name}-RangePrivateRouteAssociation",
            subnet_id=public_vpc_private_subnet.id,
            route_table_id=nat_route_table.id,
        )

        # --- Transit Gateway ---
        tgw = Ec2TransitGateway(self, f"{range_name}-TransitGateway",
            description="Transit Gateway for internal routing",
            tags={
                "Name": "tgw"
            }
        )

        # --- TGW Route to NAT Gateway (via Public VPC Attachment) ---
        # This route directs traffic destined for the internet (0.0.0.0/0) coming *from*
        # the private VPCs *towards* the Public VPC attachment ENI (which is in public_subnet inside jumpbox_vpc).
        # The private_route_table then directs it to the NAT GW.
        # Create a Transit Gateway Route Table
        # tgw_rt = Ec2TransitGatewayRouteTable(
        #     self,
        #     f"{range_name}-TGWRouteTable",
        #     transit_gateway_id=tgw.id,
        #     tags={"Name": "my-tgw-rt"}
        # )

        # --- Public VPC TGW Attachment ---
        public_vpc_tgw_attachment = Ec2TransitGatewayVpcAttachment(self, f"{range_name}-PublicVpcTgwAttachment",
            subnet_ids=[public_vpc_private_subnet.id],
            transit_gateway_id=tgw.id,
            vpc_id=jumpbox_vpc.id,
            transit_gateway_default_route_table_association=True,
            transit_gateway_default_route_table_propagation=True,
            tags={
                "Name": "public-vpc-tgw-attachment"
            }
        )

        tgw_internet_route = Ec2TransitGatewayRoute(self, f"{range_name}-TgwInternetRoute",
            destination_cidr_block="0.0.0.0/0",
            transit_gateway_attachment_id=public_vpc_tgw_attachment.id,
            transit_gateway_route_table_id=tgw.association_default_route_table_id,
        )

        # --- Store private VPC resources for reference ---
        private_vpcs = []
        private_subnets = []
        private_instances = []
        private_vpc_tgw_attachments = []

        for vpc in template_range.vpcs:

            # Step 1: Create a VPC
            new_vpc = Vpc(
                self,
                f"{range_name}-{vpc.name}",
                cidr_block=str(vpc.cidr),
                enable_dns_support=True,
                enable_dns_hostnames=True,
                tags={"Name": vpc.name},
            )
            private_vpcs.append(new_vpc)

            # Shared security group for all internal resources
            private_vpc_sg = SecurityGroup(
                self,
                f"{range_name}-{vpc.name}-SharedPrivateSG",
                vpc_id=new_vpc.id,
                tags={"Name": "RangePrivateInternalSecurityGroup"},
            )

            SecurityGroupRule(
                self,
                f"{range_name}-{vpc.name}-RangeAllowAllTrafficFromJumpBox-Rule",
                type="ingress",
                from_port=0,
                to_port=0,
                protocol="-1",
                cidr_blocks=["10.255.99.0/24"],
                security_group_id=private_vpc_sg.id,
            )

            SecurityGroupRule(
                self,
                f"{range_name}-{vpc.name}-RangeAllowInternalTraffic-Rule",  # Allow all internal subnets to communicate with each other
                type="ingress",
                from_port=0,
                to_port=0,
                protocol="-1",
                cidr_blocks=["0.0.0.0/0"],
                security_group_id=private_vpc_sg.id,
            )

            SecurityGroupRule(
                self,
                f"{range_name}-{vpc.name}-RangeAllowPrivateOutbound-Rule",
                type="egress",
                from_port=0,
                to_port=0,
                protocol="-1",
                cidr_blocks=["0.0.0.0/0"],
                security_group_id=private_vpc_sg.id,
            )

            current_vpc_subnets = []
            # Step 12: Create private subnets with their respecitve EC2 instances
            for subnet in vpc.subnets:
                new_subnet = Subnet(
                    self,
                    f"{range_name}-{vpc.name}-{subnet.name}",
                    vpc_id=new_vpc.id,
                    cidr_block=str(subnet.cidr),
                    availability_zone="us-east-1a",
                    tags={"Name": subnet.name},
                )

                private_subnets.append(new_subnet)
                current_vpc_subnets.append(new_subnet)

                # Create specified instances in the given subnet
                for host in subnet.hosts:
                    ec2_instance = Instance(
                        self,
                        f"{range_name}-{vpc.name}-{subnet.name}-{host.hostname}",
                        # WIll need to grab from update OpenLabsRange object
                        ami=AWS_OS_MAP[host.os],
                        instance_type=AWS_SPEC_MAP[host.spec],
                        subnet_id=new_subnet.id,
                        vpc_security_group_ids=[private_vpc_sg.id],
                        key_name=key_pair.key_name,  # Use the generated key pair
                        tags={"Name": host.hostname},
                    )
                    private_instances.append(ec2_instance)

            # Create Private Route Table (Routes to TGW)
            private_route_table = RouteTable(self, f"{range_name}-{vpc.name}-PrivateRouteTable",
                vpc_id=new_vpc.id,
                tags={
                    "Name": f"{vpc.name}-private-route-table"
                }
            )

            # Attach Private VPC to Transit Gateway
            private_vpc_tgw_attachment = Ec2TransitGatewayVpcAttachment(self, f"{range_name}-{vpc.name}-PrivateVpcTgwAttachment",
                subnet_ids=[s.id for s in current_vpc_subnets], # Attach TGW ENIs to all private subnets
                transit_gateway_id=tgw.id,
                vpc_id=new_vpc.id,
                transit_gateway_default_route_table_association=True,
                transit_gateway_default_route_table_propagation=True,
                tags={
                    "Name": f"{vpc.name}-private-vpc-tgw-attachment"
                }
            )
            private_vpc_tgw_attachments.append(private_vpc_tgw_attachment)

            # Default route for private subnet to Transit Gateway
            tgw_route = Route(self, f"{range_name}-{vpc.name}-PrivateTgwRoute",
                route_table_id=private_route_table.id,
                destination_cidr_block="0.0.0.0/0", # All traffic goes to TGW
                transit_gateway_id=tgw.id,
            )

            # Associate Private Subnets with Private Route Table
            for i, subnet in enumerate(current_vpc_subnets):
                 RouteTableAssociation(self, f"{range_name}-{vpc.name}-PrivateSubnetRouteTableAssociation_{i+1}",
                    subnet_id=subnet.id,
                    route_table_id=private_route_table.id
                )
                 
            # --- Add routes in PUBLIC VPC to reach this PRIVATE VPC via TGW ---
            # Add route to the *Public* VPC's *Public* route table (for Jumpbox access & NAT Return Traffic)
            Route(self, f"{range_name}-{vpc.name}-PublicRtbToPrivateVpcRoute",
                route_table_id=jumpbox_route_table.id, # Route in the public subnet's RT
                destination_cidr_block=new_vpc.cidr_block,
                transit_gateway_id=tgw.id,
            )

            # Add route to the *Public* VPC's *TGW Subnet* route table (for TGW -> Private VPC traffic, though propagation often handles this)
            # This ensures traffic arriving *from* the TGW destined for another private VPC goes back *to* the TGW
            Route(self, f"{range_name}-{vpc.name}-PublicVpcTgwSubnetRtbToPrivateVpcRoute",
                route_table_id=nat_route_table.id, # Route in the TGW attachment subnet's RT
                destination_cidr_block=new_vpc.cidr_block,
                transit_gateway_id=tgw.id,
            )

        # --- Outputs ---
        TerraformOutput(self, "JumpboxPublicIp",
            value=jumpbox.public_ip,
            description="Public IP address of the Jumpbox instance"
        )
        TerraformOutput(self, "JumpboxInstanceId",
            value=jumpbox.id,
            description="Instance ID of the Jumpbox instance"
        )

        for i, instance in enumerate(private_instances):
             TerraformOutput(self, f"{range_name}-PrivateInstance{i+1}PrivateIp",
                 value=instance.private_ip,
                 description=f"Private IP for instance with IP {instance.private_ip}"
             )
