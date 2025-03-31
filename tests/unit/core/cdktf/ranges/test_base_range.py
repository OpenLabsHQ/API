import json
import os
import shutil
import subprocess
import uuid
from typing import Callable

import pytest

from src.app.core.cdktf.ranges.aws_range import AWSRange
from src.app.core.cdktf.ranges.base_range import AbstractBaseRange
from src.app.enums.regions import OpenLabsRegion
from src.app.schemas.secret_schema import SecretSchema
from src.app.schemas.template_range_schema import TemplateRangeSchema
from src.app.schemas.user_schema import UserID
from tests.unit.core.cdktf.cdktf_mocks import (
    DummyPath,
    fake_open,
    fake_run_exception,
    fake_subprocess_run_cpe,
)
from tests.unit.core.cdktf.config import one_all_template

# NOTE:
# This file is for testing base_range.py and the AbstractBaseRange class. Because
# the class is abstract we can't instantiate it and test it directly, so the AWSRange
# class is used instead as a stand in.


@pytest.fixture(scope="function")
def aws_range(
    range_factory: Callable[
        [type[AbstractBaseRange], TemplateRangeSchema, OpenLabsRegion],
        AbstractBaseRange,
    ],
) -> AbstractBaseRange:
    """Synthesize AWS stack with one_all_template."""
    # Call the factory with the desired stack, stack name, and region.
    return range_factory(AWSRange, one_all_template, OpenLabsRegion.US_EAST_1)


def test_base_range_synthesize_exception(
    aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that aws range synthesize() returns False on exception."""

    def fake_get_provider_stack_class() -> None:
        msg = "Forced exception in get_provider_stack_class"
        raise Exception(msg)

    # Patch get_provider_stack_class with the fake function.
    monkeypatch.setattr(
        aws_range, "get_provider_stack_class", fake_get_provider_stack_class
    )

    # Calling synthesize() should now catch the exception and return False.
    result = aws_range.synthesize()
    assert result is False


def test_base_range_not_synthesized_state_on_init(aws_range: AWSRange) -> None:
    """Test that aws range objects sythesized state variable is false on init."""
    assert not aws_range.is_synthesized()


def test_base_range_sythesized_state_after_synth(aws_range: AWSRange) -> None:
    """Test that aws range objects synthesized state variable is truth after synth() call."""
    assert aws_range.synthesize()
    assert aws_range.is_synthesized()


def test_base_range_no_destroy_not_synthesized(aws_range: AWSRange) -> None:
    """Test that aws range.destroy() returns false when range object not synthesized yet."""
    assert not aws_range.destroy()


def test_base_range_no_deploy_not_synthesized(aws_range: AWSRange) -> None:
    """Test that the aws range.deploy() returns false when range object not synthesized yet."""
    assert not aws_range.deploy()


def test_base_range_not_deployed_state_when_no_state_file_init(
    aws_range: AWSRange,
) -> None:
    """Test that the aws range is_deployed state variable is false when no state_file is passed in on init."""
    assert not aws_range.is_deployed()


def test_base_range_init_with_state_file() -> None:
    """Test that is_deployed() returns True when we initialize with a state_file."""
    test_state_file = {"test": "Test content"}

    aws_range = AWSRange(
        id=uuid.uuid4(),
        name="test-range",
        template=one_all_template,
        region=OpenLabsRegion.US_EAST_1,
        owner_id=UserID(id=uuid.uuid4()),
        secrets=SecretSchema(),
        state_file=test_state_file,
    )

    assert aws_range.is_deployed()


def test_base_range_get_state_file_none_when_no_state_file_init(
    aws_range: AWSRange,
) -> None:
    """Test that the aws range get_state_file() returns None when no state_file is passed in on init."""
    assert aws_range.get_state_file() is None


def test_base_range_get_state_file_with_content(aws_range: AWSRange) -> None:
    """Test that aws range get_state_file() returns the state_file variable content."""
    test_state_file = {"test": "Test content"}
    aws_range.state_file = test_state_file
    assert aws_range.get_state_file() == test_state_file


def test_base_range_get_state_file_path(aws_range: AWSRange) -> None:
    """Test that the aws range get_state_file_path() returns the correct path."""
    correct_path = (
        aws_range.get_synth_dir() / f"terraform.{aws_range.stack_name}.tfstate"
    )
    assert aws_range.get_state_file_path() == correct_path


def test_base_range_create_state_file_no_content(aws_range: AWSRange) -> None:
    """Test that the aws range create_state_file() returns false when no state_file content available."""
    assert not aws_range.create_state_file()


def test_base_range_create_state_file(aws_range: AWSRange) -> None:
    """Test that the aws range create_state_file() creates a correct state file."""
    test_state_file = {"test": "Test content"}
    aws_range.state_file = test_state_file

    assert aws_range.synthesize()
    assert aws_range.create_state_file()

    # Test correct content
    state_file_content = ""
    with open(aws_range.get_state_file_path(), mode="r") as file:
        state_file_content = file.read()

    assert state_file_content, "State file is empty when it should have content!"

    loaded_state_file_content = json.loads(state_file_content)
    assert loaded_state_file_content == test_state_file


def test_base_range_cleanup_synth(aws_range: AWSRange) -> None:
    """Test that aws range cleanup_synth() works after synthesis."""
    assert aws_range.synthesize(), "Failed to synthesize AWS range object!"
    assert aws_range.cleanup_synth()


def test_base_range_cleanup_synth_exception(
    aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that aws range cleanup_synth() returns False on exception."""

    # Define a fake rmtree function that always raises an exception.
    def fake_rmtree(path: str, ignore_errors: bool = False) -> None:
        msg = "Forced exception for testing"
        raise OSError(msg)

    # Override shutil.rmtree with our fake function.
    monkeypatch.setattr(shutil, "rmtree", fake_rmtree)

    # Call the cleanup_synth method; it should catch the exception and return False.
    result = aws_range.cleanup_synth()
    assert result is False


def test_base_range_deploy_success(
    aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that deploy() returns True when subprocess commands succeed."""
    # Ensure the range is synthesized
    monkeypatch.setattr(aws_range, "is_synthesized", lambda: True)

    # Patch subprocess.run to simulate successful execution (no exceptions raised)
    monkeypatch.setattr(subprocess, "run", lambda cmd, check, **kwargs: None)

    # Patch os.chdir to prevent actual directory changes
    monkeypatch.setattr(os, "chdir", lambda x: None)

    # Create a dummy Path-like object for get_state_file_path and get_synth_dir
    dummy_path = DummyPath()
    dummy_path.exists.return_value = True

    monkeypatch.setattr(aws_range, "get_state_file_path", lambda: DummyPath())
    monkeypatch.setattr(aws_range, "get_synth_dir", lambda: DummyPath())

    # Patch cleanup_synth to simulate successful cleanup
    monkeypatch.setattr(aws_range, "cleanup_synth", lambda: True)

    # Patch open to simulate reading a valid JSON state file
    monkeypatch.setattr(
        "builtins.open",
        fake_open,
    )

    result = aws_range.deploy()
    assert result is True


def test_base_range_deploy_calledprocesserror(
    aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that deploy() returns False when subprocess.run raises CalledProcessError."""
    monkeypatch.setattr(aws_range, "is_synthesized", lambda: True)
    monkeypatch.setattr(subprocess, "run", fake_subprocess_run_cpe)
    monkeypatch.setattr(os, "chdir", lambda x: None)

    # Create a dummy Path-like object for get_state_file_path and get_synth_dir
    dummy_path = DummyPath()
    dummy_path.exists.return_value = True

    monkeypatch.setattr(aws_range, "get_state_file_path", lambda: DummyPath())
    monkeypatch.setattr(aws_range, "cleanup_synth", lambda: True)

    result: bool = aws_range.deploy()
    assert result is False


def test_base_range_deploy_exception(
    aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that deploy() returns False when subprocess.run raises a general exception."""
    monkeypatch.setattr(aws_range, "is_synthesized", lambda: True)
    monkeypatch.setattr(subprocess, "run", fake_run_exception)
    monkeypatch.setattr(os, "chdir", lambda x: None)

    # Create a dummy Path-like object for get_state_file_path and get_synth_dir
    dummy_path = DummyPath()
    dummy_path.exists.return_value = True

    monkeypatch.setattr(aws_range, "get_state_file_path", lambda: DummyPath())
    monkeypatch.setattr(aws_range, "cleanup_synth", lambda: True)

    result: bool = aws_range.deploy()
    assert result is False


def test_base_range_deploy_no_state_file(
    aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that deploy() returns False when no state file is found after deploying the range."""
    # Ensure the range is synthesized
    monkeypatch.setattr(aws_range, "is_synthesized", lambda: True)

    # Patch subprocess.run to simulate successful execution (no exceptions raised)
    monkeypatch.setattr(subprocess, "run", lambda cmd, check, **kwargs: None)

    # Patch os.chdir to prevent actual directory changes
    monkeypatch.setattr(os, "chdir", lambda x: None)

    # Create a dummy Path-like object that returns False to simulate no state file
    dummy_path_no_exist = DummyPath()
    dummy_path_no_exist.exists.return_value = False

    monkeypatch.setattr(aws_range, "get_state_file_path", lambda: dummy_path_no_exist)
    monkeypatch.setattr(aws_range, "get_synth_dir", lambda: DummyPath())

    result = aws_range.deploy()
    assert result is False


def test_base_range_destroy_success(
    aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that destroy() returns True when subprocess commands succeed."""
    # Ensure the range is deployed and synthesized
    monkeypatch.setattr(aws_range, "is_deployed", lambda: True)
    monkeypatch.setattr(aws_range, "is_synthesized", lambda: True)

    # Simulate successful creation of the state file
    monkeypatch.setattr(aws_range, "create_state_file", lambda: True)

    # Return empty credential environment variables
    monkeypatch.setattr(aws_range, "get_cred_env_vars", lambda: {})

    # Patch subprocess.run to simulate successful execution (no exceptions)
    monkeypatch.setattr(subprocess, "run", lambda cmd, check, **kwargs: None)

    # Prevent actual directory changes
    monkeypatch.setattr(os, "chdir", lambda x: None)

    # Patch get_synth_dir to return a DummyPath instance
    monkeypatch.setattr(aws_range, "get_synth_dir", lambda: DummyPath())

    # Simulate successful cleanup of synthesis files
    monkeypatch.setattr(aws_range, "cleanup_synth", lambda: True)

    result = aws_range.destroy()
    assert result is True


def test_base_range_destroy_calledprocesserror(
    aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that destroy() returns False when subprocess.run raises CalledProcessError."""
    monkeypatch.setattr(aws_range, "is_deployed", lambda: True)
    monkeypatch.setattr(aws_range, "is_synthesized", lambda: True)
    monkeypatch.setattr(aws_range, "create_state_file", lambda: True)
    monkeypatch.setattr(aws_range, "get_cred_env_vars", lambda: {})

    # Patch subprocess.run to raise a CalledProcessError
    monkeypatch.setattr(subprocess, "run", fake_subprocess_run_cpe)
    monkeypatch.setattr(os, "chdir", lambda x: None)
    monkeypatch.setattr(aws_range, "get_synth_dir", lambda: DummyPath())
    monkeypatch.setattr(aws_range, "cleanup_synth", lambda: True)

    result = aws_range.destroy()
    assert result is False


def test_base_range_destroy_create_state_file_failure(
    aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that destroy() returns False when create_state_file() fails."""
    monkeypatch.setattr(aws_range, "is_deployed", lambda: True)
    monkeypatch.setattr(aws_range, "is_synthesized", lambda: True)
    monkeypatch.setattr(aws_range, "get_synth_dir", lambda: DummyPath())

    # Prevent actual directory changes
    monkeypatch.setattr(os, "chdir", lambda x: None)

    # Simulate failure in state file creation
    monkeypatch.setattr(aws_range, "create_state_file", lambda: False)

    result = aws_range.destroy()
    assert result is False


def test_base_range_destroy_not_synthesized(
    aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that destroy() returns False when it's not synthesized."""
    monkeypatch.setattr(aws_range, "is_deployed", lambda: True)
    monkeypatch.setattr(aws_range, "is_synthesized", lambda: False)

    result = aws_range.destroy()
    assert result is False
