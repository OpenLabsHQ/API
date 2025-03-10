from pathlib import Path

from cdktf import LocalBackend, TerraformStack
from constructs import Construct

from ....enums.regions import OpenLabsRegion
from ....schemas.template_range_schema import TemplateRangeSchema


class AbstractBaseStack(TerraformStack):
    """A 'pseudo-abstract' base class that extends TerraformStack.

    Simulates abstract methods by raising a NotImplementedError for the
    "psuedo-abstract" functions.
    """

    def __init__(
        self,
        scope: Construct,
        template_range: TemplateRangeSchema,
        cdktf_id: str,
        cdktf_dir: str,
        region: OpenLabsRegion,
    ) -> None:
        """Initialize AWS terraform stack.

        Args:
        ----
            self (AWSStack): AWSStack class.
            scope (Construct): CDKTF app
            template_range: Range object used for create all necessary resources to deploy
            cdktf_id (str): Unique ID for CDKTF app
            cdktf_dir (str): Directory location for all terraform files
            region (OpenLabsRegion): Supported OpenLabs cloud region.
            secrets (SecretSchema): Cloud secrets.

        Returns:
        -------
            None

        """
        super().__init__(scope, cdktf_id)

        LocalBackend(
            self,
            path=str(
                Path(f"{cdktf_dir}/stacks/{cdktf_id}/terraform.{cdktf_id}.tfstate")
            ),
        )

        # Will raise NotImplementedError when not-overriden by child class
        self.build_resources(template_range=template_range, region=region)

    def build_resources(
        self,
        template_range: TemplateRangeSchema,
        region: OpenLabsRegion,
    ) -> None:
        """'Psuedo-abtract' method to build the CDKTF resources.

        Args:
        ----
            template_range (TemplateRangeSchema): Template range object to build terraform for.
            region (OpenLabsRegion): Support OpenLabs cloud region.
            secrets (SecretScehma): Cloud secrets.

        Returns:
        -------
            None

        """
        msg = "Subclasses of AbstractBaseStack must implement build_resources()."
        raise NotImplementedError(msg)
