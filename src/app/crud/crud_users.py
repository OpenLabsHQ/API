import logging
from datetime import UTC, datetime
from uuid import UUID

from bcrypt import checkpw, gensalt, hashpw
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import load_only

from ..models.secret_model import SecretModel
from ..models.user_model import UserModel
from ..schemas.secret_schema import SecretSchema
from ..schemas.user_schema import (
    UserCreateBaseSchema,
    UserCreateSchema,
    UserID,
)
from ..utils.crypto import (
    decrypt_private_key,
    decrypt_with_private_key,
    encrypt_private_key,
    generate_master_key,
    generate_rsa_key_pair,
)

logger = logging.getLogger(__name__)


async def create_secret(
    db: AsyncSession, secret: SecretSchema, user_id: UserID
) -> SecretModel:
    """Create a new secret.

    Args:
    ----
        db (AsyncSession): Database connection.
        secret (SecretSchema): Secret data.
        user_id (UserID): ID of the user who owns this secret.

    Returns:
    -------
        SecretModel: The created secret.

    """
    secret_dict = secret.model_dump()
    secret_dict["user_id"] = user_id.id

    secret_obj = SecretModel(**secret_dict)
    db.add(secret_obj)

    return secret_obj


async def get_user(db: AsyncSession, email: str) -> UserModel | None:
    """Get a user by email.

    Args:
    ----
        db (Session): Database connection.
        email (str): User email.

    Returns:
    -------
        User: The user.

    """
    mapped_user_model = inspect(UserModel)
    main_columns = [
        getattr(UserModel, attr.key) for attr in mapped_user_model.column_attrs
    ]

    stmt = (
        select(UserModel)
        .where(UserModel.email == email)
        .options(load_only(*main_columns))
    )

    result = await db.execute(stmt)

    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: UserID) -> UserModel | None:
    """Get a user by ID.

    Args:
    ----
        db (Session): Database connection.
        user_id (UserID): User ID.

    Returns:
    -------
        User: The user.

    """
    mapped_user_model = inspect(UserModel)
    main_columns = [
        getattr(UserModel, attr.key) for attr in mapped_user_model.column_attrs
    ]

    stmt = (
        select(UserModel)
        .where(UserModel.id == user_id.id)
        .options(load_only(*main_columns))
    )

    result = await db.execute(stmt)

    return result.scalars().first()


async def create_user(
    db: AsyncSession, openlabs_user: UserCreateBaseSchema, is_admin: bool = False
) -> UserModel:
    """Create and add a new OpenLabsUser to the database.

    Args:
    ----
        db (Session): Database connection.
        openlabs_user (UserBaseSchema): Dictionary containing User data.
        is_admin (bool): Whether the user should be an admin. Defaults to False.

    Returns:
    -------
        User: The newly created user.

    """
    openlabs_user = UserCreateSchema(**openlabs_user.model_dump())
    user_dict = openlabs_user.model_dump(exclude={"secrets"})

    # Here, we populate fields to match the database model
    password = user_dict.pop("password")

    # Generate bcrypt password hash
    hash_salt = gensalt()
    hashed_password = hashpw(password.encode(), hash_salt)
    user_dict["hashed_password"] = hashed_password.decode()

    # Generate RSA key pair
    private_key_b64, public_key_b64 = generate_rsa_key_pair()

    # Generate master key from password using Argon2
    master_key, key_salt = generate_master_key(password)

    # Encrypt the private key with the master key
    encrypted_private_key_b64 = encrypt_private_key(private_key_b64, master_key)

    # Store public key, encrypted private key and salt in user record
    user_dict["public_key"] = public_key_b64
    user_dict["encrypted_private_key"] = encrypted_private_key_b64
    user_dict["key_salt"] = key_salt

    user_dict["created_at"] = datetime.now(UTC)
    user_dict["last_active"] = datetime.now(UTC)

    user_dict["is_admin"] = is_admin

    user_obj = UserModel(**user_dict)
    db.add(user_obj)

    user_id = UserID(id=user_obj.id)

    empty_secret = SecretSchema()

    secrets_object = await create_secret(db, empty_secret, user_id)

    db.add(secrets_object)

    await db.commit()

    return user_obj


async def get_decrypted_secrets(
    user: UserModel, db: AsyncSession, master_key: bytes
) -> SecretSchema | None:
    """Get decrypted secrets for the user.

    Args:
    ----
        user (UserModel): The user whose secrets to decrypt
        db (AsyncSession): Database connection
        master_key (bytes): The decryption master key

    Returns:
    -------
        SecretSchema | None: A schema containing decrypted secrets, or None if decryption fails

    """
    if not master_key or not user.encrypted_private_key:
        return None

    # Fetch the user's secrets from the database
    mapped_secret_model = inspect(SecretModel)
    main_columns = [
        getattr(SecretModel, attr.key) for attr in mapped_secret_model.column_attrs
    ]

    stmt = (
        select(SecretModel)
        .where(SecretModel.user_id == user.id)
        .options(load_only(*main_columns))
    )

    result = await db.execute(stmt)
    secrets = result.scalars().first()

    if not secrets:
        return None

    try:
        # Decrypt the private key
        private_key_b64 = decrypt_private_key(user.encrypted_private_key, master_key)

        # Create a new SecretSchema for the decrypted secrets
        decrypted_secrets = SecretSchema(
            aws_created_at=secrets.aws_created_at,
            azure_created_at=secrets.azure_created_at,
        )

        # Decrypt AWS secrets if they exist
        if secrets.aws_access_key and secrets.aws_secret_key:
            encrypted_aws = {
                "aws_access_key": secrets.aws_access_key,
                "aws_secret_key": secrets.aws_secret_key,
            }
            decrypted_aws = decrypt_with_private_key(encrypted_aws, private_key_b64)
            decrypted_secrets.aws_access_key = decrypted_aws["aws_access_key"]
            decrypted_secrets.aws_secret_key = decrypted_aws["aws_secret_key"]

        # Decrypt Azure secrets if they exist
        if (
            secrets.azure_client_id
            and secrets.azure_client_secret
            and secrets.azure_tenant_id
            and secrets.azure_subscription_id
        ):
            encrypted_azure = {
                "azure_client_id": secrets.azure_client_id,
                "azure_client_secret": secrets.azure_client_secret,
                "azure_tenant_id": secrets.azure_tenant_id,
                "azure_subscription_id": secrets.azure_subscription_id,
            }
            decrypted_azure = decrypt_with_private_key(encrypted_azure, private_key_b64)
            decrypted_secrets.azure_client_id = decrypted_azure["azure_client_id"]
            decrypted_secrets.azure_client_secret = decrypted_azure[
                "azure_client_secret"
            ]
            decrypted_secrets.azure_tenant_id = decrypted_azure["azure_tenant_id"]
            decrypted_secrets.azure_subscription_id = decrypted_azure[
                "azure_subscription_id"
            ]

        return decrypted_secrets
    except Exception:
        logger.warning(
            "Failed to decrypt secret when getting a secret for user: %s (%s)",
            user.name,
            user.id,
        )
        return None


async def update_user_password(
    db: AsyncSession, user_id: UUID, current_password: str, new_password: str
) -> bool:
    """Update a user's password.

    Args:
    ----
        db (AsyncSession): Async database connection.
        user_id (UUID): User ID.
        current_password (str): Current password.
        new_password (str): New password.

    Returns:
    -------
        bool: True if the password was successfully updated, False otherwise.

    """
    # Get the user
    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        return False

    # Check if the current password is correct
    if not checkpw(current_password.encode(), user.hashed_password.encode()):
        return False

    # Hash the new password
    hash_salt = gensalt()
    hashed_password = hashpw(new_password.encode(), hash_salt)

    # We need to decrypt the private key with the old master key and re-encrypt it with the new one
    if user.encrypted_private_key and user.key_salt:
        # Generate the old master key using the current password and stored salt
        old_master_key, _ = generate_master_key(current_password, user.key_salt)

        # Decrypt the private key using the old master key
        try:
            private_key_b64 = decrypt_private_key(
                user.encrypted_private_key, old_master_key
            )

            # Generate a new master key and salt
            new_master_key, new_key_salt = generate_master_key(new_password)

            # Re-encrypt the private key with the new master key
            new_encrypted_private_key = encrypt_private_key(
                private_key_b64, new_master_key
            )

            # Update the user's encrypted private key and salt
            user.encrypted_private_key = new_encrypted_private_key
            user.key_salt = new_key_salt
        except Exception:
            logger.warning(
                "Failed to decrypt secret when updating a secret for user: %s (%s)",
                user.name,
                user.id,
            )
            return False

    # Update the user's password
    user.hashed_password = hashed_password.decode()
    await db.commit()

    return True
