import json
import logging
import os
import shutil
import subprocess
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from cdktf import App

from ....enums.regions import OpenLabsRegion
from ....schemas.secret_schema import SecretSchema
from ....schemas.template_range_schema import TemplateRangeSchema
from ....schemas.user_schema import UserID
from ...config import settings
from ..stacks.base_stack import AbstractBaseStack

# Configure logging
logger = logging.getLogger(__name__)


class AbstractBaseRange(ABC):
    """Abstract class to enforce common functionality across range cloud providers."""

    id: uuid.UUID
    name: str
    template: TemplateRangeSchema
    state_file: dict[str, Any] | None  # Terraform state
    region: OpenLabsRegion
    stack_name: str
    owner_id: UserID
    secrets: SecretSchema

    # State varibles
    _is_synthesized: bool
    _is_deployed: bool

    def __init__(  # noqa: PLR0913
        self,
        id: uuid.UUID,  # noqa: A002
        name: str,
        template: TemplateRangeSchema,
        region: OpenLabsRegion,
        owner_id: UserID,
        secrets: SecretSchema,
        state_file: dict[str, Any] | None = None,
    ) -> None:
        """Initialize CDKTF base range object."""
        self.id = id
        self.name = name
        self.template = template
        self.region = region
        self.owner_id = owner_id
        self.secrets = secrets
        self.state_file = state_file
        if not self.state_file:
            self._is_deployed = False
        else:
            self._is_deployed = True

        # Initial values
        self.stack_name = f"{self.template.name}-{self.id}"
        self._is_synthesized = False

    @abstractmethod
    def get_provider_stack_class(self) -> type[AbstractBaseStack]:
        """Return specific provider stack class to instantiate.

        Returns
        -------
        type[AbstractBaseStack]: Provider stack class.

        """
        pass

    @abstractmethod
    def has_secrets(self) -> bool:
        """Return if range has correct provider cloud credentials.

        Returns
        -------
            bool: True if correct provider creds exist. False otherwise.

        """
        pass

    @abstractmethod
    def get_cred_env_vars(self) -> dict[str, Any]:
        """Return dictionary of BASH Terraform cloud credential environment variables.

        Returns
        -------
            dict[str, Any]: Dict of BASH environment variables.

        """
        pass

    def synthesize(self) -> bool:
        """Abstract method to synthesize terraform configuration.

        Returns:
            bool: True if successful synthesis. False otherwise.

        """
        try:
            logger.info("Synthesizing selected range: %s (%s)", self.name, self.id)

            # Create CDKTF app
            app = App(outdir=settings.CDKTF_DIR)

            # Instantiate the correct provider stack
            stack_class = self.get_provider_stack_class()
            stack_class(
                scope=app,
                template_range=self.template,
                cdktf_id=self.stack_name,
                cdktf_dir=settings.CDKTF_DIR,
                region=self.region,
                range_name=self.name,
            )

            # Synthesize Terraform files
            app.synth()
            logger.info(
                "Template: %s synthesized successfully as Stack: %s",
                self.template.name,
                self.stack_name,
            )

            self._is_synthesized = True
            return True
        except Exception as e:
            logger.error(
                "Caught exception during synthesis of stack %s. Type: %s, Args: %s",
                self.stack_name,
                type(e).__name__,
                e.args,
            )
            # Use logger.exception to automatically include the traceback
            logger.exception(
                "Traceback for synthesis error in stack %s:", self.stack_name
            )
            return False

    def deploy(self) -> bool:
        """Run `terraform deploy --auto-approve` programmatically.

        Returns
        -------
            bool: True if successfully deployed range. False otherwise.

        """
        if not self.is_synthesized():
            logger.error("Range to destroy is not synthesized!")
            return False

        try:
            initial_dir = os.getcwd()
            os.chdir(self.get_synth_dir())
            subprocess.run(["terraform", "init"], check=True)  # noqa: S603, S607

            # Terraform apply
            env = os.environ.copy()
            env.update(self.get_cred_env_vars())
            logger.info("Deploying selected range: %s (%s)", self.name, self.id)
            subprocess.run(  # noqa: S603
                ["terraform", "apply", "--auto-approve"],  # noqa: S607
                check=True,
                env=env,
            )

            # Load state
            state_file_path = self.get_state_file_path()
            if state_file_path.exists():
                with open(state_file_path, "r", encoding="utf-8") as file:
                    self.state_file = json.loads(file.read())
            else:
                logger.error(
                    "State file was not created during deployment. Expected path: %s",
                    state_file_path,
                )
                return False

            self._is_deployed = True
            logger.info(
                "Successfully deployed range: %s (%s)", self.template.name, self.id
            )

            # Delete files made during deployment
            os.chdir(initial_dir)
            self.cleanup_synth()
            return True
        except subprocess.CalledProcessError as e:
            logger.error("Terraform command failed: %s", e)
            logger.exception(
                "Traceback for deploy subprocess error in stack %s:", self.stack_name
            )
            return False
        except Exception as e:
            logger.error("Error during deployment: %s", e)
            logger.exception("Traceback for deploy error in stack %s:", self.stack_name)
            return False

    def destroy(self) -> bool:
        """Destroy terraform infrastructure.

        Args:
        ----
            stack_dir (str): Output directory.
            stack_name (str): Name of stack used to deploy the range (format: <range name>-<range id>) to tear down the range.

        Returns:
        -------
            None

        """
        if not self.is_deployed():
            logger.error("Can't destroy range that is not deployed!")
            return False

        if not self.is_synthesized():
            logger.error("Range to destory is not synthesized!")
            return False

        try:
            # Change to directory with `cdk.tf.json`
            initial_dir = os.getcwd()
            os.chdir(self.get_synth_dir())
            if not self.create_state_file():
                msg = f"Unable to destroy range: {self.template.name} ({self.id}) missing state file!"
                raise ValueError(msg)

            # Run Terraform commands
            env = os.environ.copy()
            env.update(self.get_cred_env_vars())
            logger.info(
                "Tearing down selected range: %s (%s)", self.template.name, self.id
            )
            subprocess.run(["terraform", "init"], check=True)  # noqa: S603, S607
            subprocess.run(  # noqa: S603
                ["terraform", "destroy", "--auto-approve"],  # noqa: S607
                check=True,
                env=env,
            )

            os.chdir(initial_dir)

            # Delete synth files
            self.cleanup_synth()
            self._is_deployed = False

            logger.info(
                "Successfully destroyed range: %s (%s)", self.template.name, self.id
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error("Terraform command failed: %s", e)
            logger.exception(
                "Traceback for destroy subprocess error in stack %s:", self.stack_name
            )
            return False
        except Exception as e:
            logger.error("Error during destroy: %s", e)
            logger.exception(
                "Traceback for destroy error in stack %s:", self.stack_name
            )
            return False

    def is_synthesized(self) -> bool:
        """Return if range is currently synthesized."""
        return self._is_synthesized

    def is_deployed(self) -> bool:
        """Return if range is currently deployed."""
        return self._is_deployed

    def get_synth_dir(self) -> Path:
        """Get CDKTF synthesis directory."""
        return Path(f"{settings.CDKTF_DIR}/stacks/{self.stack_name}")

    def get_synth_file_path(self) -> Path:
        """Get path to terraform HCL from CDKTF synthesis."""
        return Path(f"{self.get_synth_dir()}/cdk.tf.json")

    def get_state_file(self) -> dict[str, Any] | None:
        """Return state file content.

        Range must have been deployed or have a state file passed on object creation.
        """
        return self.state_file

    def get_state_file_path(self) -> Path:
        """Get CDKTF state file path."""
        return self.get_synth_dir() / f"terraform.{self.stack_name}.tfstate"

    def create_state_file(self) -> bool:
        """Create state file with contents.

        Range must have been deployed or have a state file passed on object creation.

        Returns
        -------
            bool: True if state file successfully written. False otherwise.

        """
        if not self.state_file:
            msg = f"Can't write state file none exists! Attempted on range: {self.id}"
            logger.warning(msg)
            return False

        with open(self.get_state_file_path(), mode="w") as file:
            json.dump(self.state_file, file, indent=4)

        msg = f"Successfully created state file: {self.get_state_file_path()} "
        logger.info(msg)
        return True

    def cleanup_synth(self) -> bool:
        """Delete Terraform files generated by CDKTF synthesis."""
        try:
            shutil.rmtree(self.get_synth_dir())
            self._is_synthesized = False
            return True
        except Exception as e:
            logger.error(
                "Failed to delete synthesis files for stack: %s. Error: %s",
                self.stack_name,
                e,
            )
            return False
