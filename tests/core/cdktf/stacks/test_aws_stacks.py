from typing import Callable

import pytest

from src.app.core.cdktf.stacks.base_stack import AbstractBaseStack
from src.app.enums.regions import OpenLabsRegion
from src.app.schemas.template_range_schema import TemplateRangeSchema
from tests.core.cdktf.config import modify_cidr, one_all_template


@pytest.fixture(scope="module")
def aws_one_all_synthesis(
    synthesize_factory: Callable[
        [type[AbstractBaseStack], TemplateRangeSchema, str, OpenLabsRegion], str
    ],
) -> str:
    """Synthesize AWS stack with one_all_template."""
    from src.app.core.cdktf.stacks.aws_stack import AWSStack

    # Call the factory with the desired stack, stack name, and region.
    return synthesize_factory(
        AWSStack,
        one_all_template,
        "aws_test_range",
        OpenLabsRegion.US_EAST_1,
    )


def test_every_vpc_is_valid(aws_one_all_synthesis: str) -> None:
    """Ensure every VPC is valid."""
    from cdktf import Testing
    from cdktf_cdktf_provider_aws.vpc import Vpc

    assert Testing.to_have_resource(aws_one_all_synthesis, Vpc.TF_RESOURCE_TYPE)

    for vpc in one_all_template.vpcs:
        assert Testing.to_have_resource_with_properties(
            aws_one_all_synthesis,
            Vpc.TF_RESOURCE_TYPE,
            {"tags": {"Name": f"{vpc.name}"}, "cidr_block": str(vpc.cidr)},
        )


def test_each_vpc_has_a_public_subnet(aws_one_all_synthesis: str) -> None:
    """Ensure each VPC has at least one public subnet."""
    from cdktf import Testing
    from cdktf_cdktf_provider_aws.subnet import Subnet

    assert Testing.to_have_resource(aws_one_all_synthesis, Subnet.TF_RESOURCE_TYPE)

    for vpc in one_all_template.vpcs:
        # Generate the new subnet CIDR with third octet = 99
        public_subnet_cidr = modify_cidr(str(vpc.cidr), 99)
        assert Testing.to_have_resource_with_properties(
            aws_one_all_synthesis,
            Subnet.TF_RESOURCE_TYPE,
            {
                "tags": {"Name": f"RangePublicSubnet-{vpc.name}"},
                "cidr_block": str(public_subnet_cidr),
            },
        )


def test_each_vpc_has_a_jumpbox_ec2_instance(aws_one_all_synthesis: str) -> None:
    """Ensure each VPC has a jumpbox EC2 instance."""
    from cdktf import Testing
    from cdktf_cdktf_provider_aws.instance import Instance

    assert Testing.to_have_resource(aws_one_all_synthesis, Instance.TF_RESOURCE_TYPE)

    for vpc in one_all_template.vpcs:
        assert Testing.to_have_resource_with_properties(
            aws_one_all_synthesis,
            Instance.TF_RESOURCE_TYPE,
            {"tags": {"Name": f"JumpBox-{vpc.name}"}},
        )


def test_each_vpc_has_at_least_one_subnet(aws_one_all_synthesis: str) -> None:
    """Ensure each VPC has at least one subnet."""
    from cdktf import Testing
    from cdktf_cdktf_provider_aws.subnet import Subnet

    assert Testing.to_have_resource(aws_one_all_synthesis, Subnet.TF_RESOURCE_TYPE)

    for vpc in one_all_template.vpcs:
        for subnet in vpc.subnets:
            assert Testing.to_have_resource_with_properties(
                aws_one_all_synthesis,
                Subnet.TF_RESOURCE_TYPE,
                {
                    "tags": {"Name": f"{subnet.name}-{vpc.name}"},
                    "cidr_block": str(subnet.cidr),
                },
            )


def test_each_subnet_has_at_least_one_ec2_instance(aws_one_all_synthesis: str) -> None:
    """Ensure each subnet has at least one EC2 instance."""
    from cdktf import Testing
    from cdktf_cdktf_provider_aws.instance import Instance

    from src.app.enums.operating_systems import AWS_OS_MAP
    from src.app.enums.specs import AWS_SPEC_MAP

    assert Testing.to_have_resource(aws_one_all_synthesis, Instance.TF_RESOURCE_TYPE)

    for vpc in one_all_template.vpcs:
        for subnet in vpc.subnets:
            for host in subnet.hosts:
                assert Testing.to_have_resource_with_properties(
                    aws_one_all_synthesis,
                    Instance.TF_RESOURCE_TYPE,
                    {
                        "tags": {"Name": f"{host.hostname}-{vpc.name}"},
                        "ami": str(AWS_OS_MAP[host.os]),
                        "instance_type": str(AWS_SPEC_MAP[host.spec]),
                    },
                )
