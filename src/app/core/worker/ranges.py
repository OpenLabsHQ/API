import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import uvloop
from arq.worker import Worker

from ...crud.crud_range_templates import get_range_template
from ...crud.crud_ranges import create_range
from ...enums.range_states import RangeState
from ...schemas.message_schema import MessageSchema
from ...schemas.range_schema import DeployRangeBaseSchema, RangeID, RangeSchema
from ...schemas.secret_schema import SecretSchema
from ...schemas.template_range_schema import TemplateRangeID, TemplateRangeSchema
from ...schemas.user_schema import UserID
from ..cdktf.ranges.range_factory import RangeFactory
from ..db.database import managed_async_get_db

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

logger = logging.getLogger(__name__)


async def deploy_range(
    ctx: Worker,
    deploy_request_dict: dict[str, Any],
    secrets_dict: dict[str, Any],
    user_id: uuid.UUID,
    is_admin: bool,
) -> RangeID:
    """Deploy a range using terraform.

    **Note:** This function currently reimplements a lot of the same error checking from the range
    deploy and destroy endpoints. These are here to act as guards and the duplicated checks left in
    the endpoints were left there to provide users with better error messages.

    Args:
    ----
        ctx (Worker): ARQ worker.
        master_key (bytes): Master key to fetch credentials
        deploy_request (DeployRangeBaseSchema): Deployment range request schema object.

    Returns:
    -------
        bool: True if successfully deployed. False otherwise.
        str: Message with details about deployment success or failure.

    """
    deploy_request = DeployRangeBaseSchema.model_validate(deploy_request_dict)
    secrets = SecretSchema.model_validate(secrets_dict)

    async with managed_async_get_db() as db:
        template_owner = None if is_admin else user_id

        # Get requested template
        template_range_model = await get_range_template(
            db=db,
            range_id=TemplateRangeID(id=deploy_request.template_id),
            user_id=template_owner,
        )
        if not template_range_model:
            msg = f"Range template with ID: {deploy_request.template_id} not found or you don't have access to it!"
            raise ValueError(msg)

        range_template = TemplateRangeSchema.model_validate(
            template_range_model, from_attributes=True
        )

        # Create range ID
        range_id = uuid.uuid4()
        logger.info("Deploying range: %s with ID: %s", deploy_request.name, range_id)

        range_obj = RangeFactory.create_range(
            id=range_id,
            name=deploy_request.name,
            template=range_template,
            region=deploy_request.region,
            owner_id=UserID(id=user_id),
            secrets=secrets,
        )

        if not range_obj.has_secrets():
            msg = f"No credentials found for provider: {range_obj.template.provider.value}"
            raise RuntimeError(msg)

        # Deploy range
        successful_synthesize = range_obj.synthesize()
        if not successful_synthesize:
            msg = f"Failed to synthesize range: {range_obj.name} ({range_obj.id}) from template: {range_obj.template.name} ({range_obj.template.id})!"
            raise RuntimeError(msg)

        successful_deploy = range_obj.deploy()
        if not successful_deploy:
            msg = f"Failed to deploy range: {range_obj.name} ({range_obj.id}) from template: {range_obj.template.name} ({range_obj.template.id})!"
            raise RuntimeError(msg)

        # Build range schema
        range_schema = RangeSchema(
            **deploy_request.model_dump(),
            id=range_obj.id,
            date=datetime.now(tz=timezone.utc),
            template=range_template.model_dump(mode="json"),
            state_file=range_obj.get_state_file(),
            state=RangeState.ON,
        )

        created_range_model = await create_range(
            db=db, range_schema=range_schema, owner_id=user_id
        )
        if not created_range_model:
            msg = f"Failed to save deployed range to database. Range: {range_obj.template.name} ({range_obj.id})"
            raise RuntimeError(msg)

    return RangeID(id=range_schema.id)


async def destroy_range(
    ctx: Worker,
    range_id: uuid.UUID,
    secrects_dict: dict[str, Any],
    user_id: uuid.UUID,
    is_admin: bool,
) -> MessageSchema:
    """Destroy range."""
    pass
