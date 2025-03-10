import logging
import uuid
from typing import Any, ClassVar, Type

from ....enums.providers import OpenLabsProvider
from ....enums.regions import OpenLabsRegion
from ....schemas.secret_schema import SecretSchema
from ....schemas.template_range_schema import TemplateRangeSchema
from ....schemas.user_schema import UserID
from .aws_range import AWSRange
from .base_range import AbstractBaseRange

# from .azure_range import AzureRange
# from .gcp_range import GCPRange

# Configure logging
logger = logging.getLogger(__name__)


class RangeFactory:
    """Create range objects."""

    _registry: ClassVar[dict[OpenLabsProvider, Type[AbstractBaseRange]]] = {
        OpenLabsProvider.AWS: AWSRange,
        # OpenLabsProvider.AZURE: AzureRange,
        # OpenLabsProvider.GCP: GCPRange
    }

    @classmethod
    def create_range(  # noqa: PLR0913
        cls,
        id: uuid.UUID,  # noqa: A002
        template: TemplateRangeSchema,
        region: OpenLabsRegion,
        owner_id: UserID,
        secrets: SecretSchema,
        state_file: dict[str, Any] | None = None,
    ) -> AbstractBaseRange:
        """Create range object.

        Args:
        ----
            cls (RangeFactory class): The RangeFactory class.
            id (uuid.UUID): The UUID for the deployed range object.
            template (TemplateRangeSchema): The range template object.
            region (OpenLabsRegion): Supported cloud region.
            owner_id (UserID): The ID of the user deploying range.
            secrets (SecretSchema): Cloud account secrets to use for deploying via terraform
            state_file (dict[str, Any]): The statefile of the deployed resources
            is_deployed (bool): Whether the range is deployed or not (true for when destroying or updating a range, false for when deploying a range template)

        Returns:
        -------
            AbstractBaseRange: Cdktf range object that can be deployed.

        """
        range_class = cls._registry.get(template.provider)

        if range_class is None:
            msg = f"Failed to build range object. Non-existent provider given: {template.provider}"
            logger.error(msg)
            raise ValueError(msg)

        return range_class(
            id=id,
            template=template,
            region=region,
            owner_id=owner_id,
            secrets=secrets,
            state_file=state_file,
        )
