import os
import subprocess
import uuid
from pathlib import Path

from cdktf import App

from ....schemas.template_range_schema import TemplateRangeSchema
from .aws_stack import AWSStack


def deploy_infrastructure(
    stack_dir: str, stack_name: str
) -> (
    str
):  # work on possibly returning something in the future for caching purposes (state file)
    """Run `terraform deploy --auto-approve` programmatically.

    Args:
    ----
        stack_dir (str): Output directory.
        stack_name (str): Name of stack used to deploy the range (format: <range name>-<range id>).

    Returns:
    -------
        str: terraform state file created from terraform apply

    """
    inital_dir = os.getcwd()

    # Change to directory with `cdk.tf.json`
    synth_output_dir = Path(f"{stack_dir}/stacks/{stack_name}")
    os.chdir(synth_output_dir)
    # state_file = synth_output_dir / Path(f"terraform.{stack_name}.tfstate")

    # Run Terraform commands
    print("Running terraform init...")
    subprocess.run(["terraform", "init"], check=True)  # noqa: S603, S607

    print("Running terraform apply...")
    subprocess.run(  # noqa: S603
        ["terraform", "apply", "--auto-approve"], check=True  # noqa: S607
    )
    print("Terraform apply complete!")

    # Read state file into string
    content = ""
    with open(f"terraform.{stack_name}.tfstate", "r", encoding="utf-8") as file:
        content = file.read()

    # # Remove terraform build files
    os.chdir(
        inital_dir
    )  # do not delete for now, jsut return to working directory in repo root
    # shutil.rmtree(stack_dir)
    return content


def destroy_infrastructure(
    stack_dir: str, stack_name: str
) -> None:  # For caching purposes, load in state file possibly from db
    """Destroy terraform infrastructure.

    Args:
    ----
      stack_dir (str): Output directory.
      stack_name (str): Name of stack used to deploy the range (format: <range name>-<range id>) to tear down the range.

    Returns:
    -------
      None

    """
    inital_dir = os.getcwd()
    # Change to directory with `cdk.tf.json` and terraform state file
    synth_output_dir = Path(f"{stack_dir}/stacks/{stack_name}")
    os.chdir(synth_output_dir)

    # Run Terraform commands
    print("Tearing down selected range")
    subprocess.run(  # noqa: S603
        ["terraform", "destroy", "--auto-approve"], check=True  # noqa: S607
    )

    # os.chdir(synth_output_dir.)

    os.chdir(inital_dir)


def create_aws_stack(
    cyber_range: TemplateRangeSchema, tmp_dir: str, deployed_range_id: uuid.UUID
) -> str:
    """Create and synthesize an AWS stack using the provided OpenLabsRange.

    Args:
    ----
        cyber_range (OpenLabsRange): OpenLabs compliant range object.
        tmp_dir (str): Temporary directory to store CDKTF files.
        deployed_range_id: (uuid.UUID): UUID of the newly deployed range

    Returns:
    -------
        str: Stack name.

    """
    stack_name = cyber_range.name + "-" + str(deployed_range_id)
    app = App(outdir=tmp_dir)
    AWSStack(app, stack_name, cyber_range, tmp_dir)

    app.synth()

    return stack_name
