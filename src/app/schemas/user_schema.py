from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


class UserBaseSchema(BaseModel):
    """Schema for user authentication."""

    email: str = Field(
        ...,
        description="Email of user",
        min_length=3,
        examples=["adam@ufsit.club", "alex@christy.com", "naresh@panch.al"],
    )

    password: str = Field(
        ..., description="Password of user", min_length=8, examples=["password123"]
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, email: str, _: ValidationInfo) -> str:
        """Check that email format is valid.

        Args:
        ----
            cls: OpenLabsUser object.
            email (str): User email address.
            info (ValidatonInfo): Validator context

        Returns:
        -------
            str: User email address.

        """
        try:
            emailinfo = validate_email(email, check_deliverability=False)

            return emailinfo.normalized
        except EmailNotValidError as e:
            msg = "Provided email address is invalid."
            raise ValueError(msg) from e


class UserCreateBaseSchema(UserBaseSchema):
    """User object for user creation in OpenLabs."""

    name: str = Field(
        ...,
        description="Full name of user",
        min_length=1,
        examples=["Adam Hassan", "Alex Christy", "Naresh Panchal"],
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, email: str, info: ValidationInfo) -> str:
        """Check that email format is valid.

        Args:
        ----
            cls: OpenLabsUser object.
            email (str): User email address.
            info (ValidatonInfo): Validator context

        Returns:
        -------
            str: User email address.

        """
        is_admin: bool = info.data.get("is_admin", False)
        try:
            # Skip deliverability check if user is admin (system default)
            if is_admin:
                emailinfo = validate_email(email, check_deliverability=False)
                return emailinfo.normalized

            # Makes a DNS query to validate deliverability
            # We do this, as users will only be added to DB on registration
            emailinfo = validate_email(email, check_deliverability=True)

            return emailinfo.normalized
        except EmailNotValidError as e:
            msg = "Provided email address is invalid."
            raise ValueError(msg) from e


class UserID(BaseModel):
    """Identity class for UserCreate."""

    id: int = Field(..., description="Unique user identifier.")

    model_config = ConfigDict(from_attributes=True)


class UserCreateSchema(UserCreateBaseSchema, UserID):
    """User creation object for OpenLabs."""

    model_config = ConfigDict(from_attributes=True)


class UserInfoResponseSchema(BaseModel):
    """User information response object for user page on OpenLabs Frontend."""

    id: int = Field(
        ...,
        description="User ID",
        examples=[1, 2, 3],
    )
    name: str = Field(
        ...,
        description="Full name of user",
        min_length=1,
        examples=["Adam Hassan", "Alex Christy", "Naresh Panchal"],
    )
    email: str = Field(
        ...,
        description="Email of user",
        min_length=3,
        examples=["adam@ufsit.club", "alex@christy.com", "naresh@panch.al"],
    )
    admin: bool = Field(
        ...,
        description="Admin status of user",
        examples=[True, False],
    )


class PasswordUpdateSchema(BaseModel):
    """Schema for updating user password."""

    current_password: str = Field(
        ...,
        description="Current password of user",
        min_length=8,
        examples=["password123"],
    )
    new_password: str = Field(
        ..., description="New password of user", min_length=8, examples=["password123!"]
    )
