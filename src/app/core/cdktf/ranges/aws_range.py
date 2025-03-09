from typing import Any

from ..stacks.aws_stack import AWSStack
from .base_range import CdktfBaseRange


class AWSRange(CdktfBaseRange):
    """Range deployed to AWS."""

    def get_provider_stack_class(self) -> type[AWSStack]:
        """Return AWSStack class."""
        return AWSStack

    def has_secrets(self) -> bool:
        """Return whether AWS range has proper credentials."""
        if (  # noqa: SIM103
            not self.secrets.aws_access_key or not self.secrets.aws_secret_key
        ):
            return False

        return True

    def get_cred_env_vars(self) -> dict[str, Any]:
        """Return AWS credential environment variables."""
        return {
            "AWS_ACCESS_KEY_ID": self.secrets.aws_access_key,
            "AWS_SECRET_ACCESS_KEY": self.secrets.aws_secret_key,
        }
