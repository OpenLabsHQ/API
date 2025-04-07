import base64
import uuid

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio.session import AsyncSession

from ...core.auth.auth import get_current_user
from ...core.cdktf.ranges.range_factory import RangeFactory
from ...core.db.database import async_get_db
from ...core.utils import queue
from ...crud.crud_range_templates import get_range_template
from ...crud.crud_ranges import delete_range, get_range, is_range_owner
from ...crud.crud_users import get_decrypted_secrets
from ...models.user_model import UserModel
from ...schemas.job import Job
from ...schemas.message_schema import MessageSchema
from ...schemas.range_schema import DeployRangeBaseSchema, RangeID, RangeSchema
from ...schemas.template_range_schema import TemplateRangeID, TemplateRangeSchema
from ...schemas.user_schema import UserID
from ...validators.id import is_valid_uuid4

router = APIRouter(prefix="/ranges", tags=["ranges"])


@router.post("/deploy", status_code=status.HTTP_201_CREATED)
async def deploy_range_from_template_endpoint(
    deploy_range: DeployRangeBaseSchema,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
    enc_key: str | None = Cookie(None, alias="enc_key", include_in_schema=False),
) -> Job:
    """Deploy range templates.

    Args:
    ----
        deploy_range (DeployRangeBaseSchema): Range template to deploy.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.
        enc_key (str): Encryption key from cookie for decrypting secrets.

    Returns:
    -------
        Job: ID of range deploy job.

    """
    # Check if we have the encryption key needed to decrypt secrets
    if not enc_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Encryption key not found. Please try logging in again.",
        )

    # Decode the encryption key
    try:
        master_key = base64.b64decode(enc_key)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid encryption key. Please try logging in again.",
        ) from e

    # Set user_id to None for admin to allow accessing any template
    user_id = None if current_user.is_admin else current_user.id

    template_range_model = await get_range_template(
        db, TemplateRangeID(id=deploy_range.template_id), user_id=user_id
    )
    if not template_range_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Range template with ID: {deploy_range.template_id} not found or you don't have access to it!",
        )

    # Create deployed range schema
    template = TemplateRangeSchema.model_validate(
        template_range_model, from_attributes=True
    )

    # Get the decrypted credentials
    decrypted_secrets = await get_decrypted_secrets(current_user, db, master_key)
    if not decrypted_secrets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decrypt cloud credentials. Please try logging in again.",
        )

    # Create deployable range object
    range_to_deploy = RangeFactory.create_range(
        id=uuid.uuid4(),
        name=deploy_range.name,
        template=template,
        region=deploy_range.region,
        owner_id=UserID(id=current_user.id),
        secrets=decrypted_secrets,
    )

    if not range_to_deploy.has_secrets():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No credentials found for provider: {template.provider.value}",
        )

    # Queue deployment job
    if not isinstance(queue.pool, Redis):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to connect to task queue!",
        )

    job = await queue.pool.enqueue_job(
        "deploy_range",
        deploy_range.model_dump(mode="json"),
        decrypted_secrets,
        current_user.id,
        current_user.is_admin,
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed queue up deployment job!",
        )

    return Job(id=job.job_id)


@router.delete("/{range_id}")
async def delete_range_endpoint(
    range_id: str,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
    enc_key: str | None = Cookie(None, alias="enc_key", include_in_schema=False),
) -> MessageSchema:
    """Destroy a deployed range.

    Args:
    ----
        range_id (str): ID of deployed range.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.
        enc_key (str): Encryption key from cookie for decrypting secrets.

    Returns:
    -------
        MessageSchema: Success message. Error otherwise.

    """
    if not is_valid_uuid4(range_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID provided is not a valid UUID4.",
        )

    # Check if we have the encryption key needed to decrypt secrets
    if not enc_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Encryption key not found. Please try logging in again.",
        )

    # Decode the encryption key
    try:
        master_key = base64.b64decode(enc_key)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid encryption key. Please try logging in again.",
        ) from e

    # For admin users, skip ownership check to allow deploying any range
    if not current_user.is_admin:
        # Check if the user is the template owner
        is_owner = await is_range_owner(
            db, RangeID(id=range_id), user_id=current_user.id
        )
        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Range with ID: {range_id} not found or you don't have access to it!",
            )

    # Set user_id to None for admin to allow accessing any range
    user_id = None if current_user.is_admin else current_user.id

    # Get range from database
    range_model = await get_range(db, RangeID(id=uuid.UUID(range_id)), user_id=user_id)

    if not range_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Range with ID: {range_id} not found or you don't have access to it!",
        )

    # Get the decrypted credentials
    decrypted_secrets = await get_decrypted_secrets(current_user, db, master_key)
    if not decrypted_secrets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decrypt cloud credentials. Please try logging in again.",
        )

    # Build range object
    range_schema = RangeSchema.model_validate(range_model)
    range_template = TemplateRangeSchema.model_validate(range_schema.template)
    range_obj = RangeFactory.create_range(
        id=range_schema.id,
        name=range_model.name,
        template=range_template,
        region=range_schema.region,
        owner_id=UserID(id=current_user.id),
        secrets=decrypted_secrets,
        state_file=range_schema.state_file,
    )

    if not range_obj.has_secrets():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No credentials found for provider: {range_obj.template.provider}",
        )

    # Destroy range
    successful_synthesize = range_obj.synthesize()
    if not successful_synthesize:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to synthesize range: {range_template.name} ({range_obj.id})!",
        )

    successful_destroy = range_obj.destroy()
    if not successful_destroy:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to destroy range: {range_template.name} ({range_obj.id})!",
        )

    # Delete range from database
    deleted_from_db = await delete_range(db, range_model)
    if not deleted_from_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete deployed range entry in database. Range: {range_obj.template.name} ({range_obj.id})",
        )

    return MessageSchema(
        message=f"Successfully destroyed range: {range_obj.name} ({range_id})"
    )
