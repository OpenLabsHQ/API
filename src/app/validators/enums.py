import logging
from enum import Enum
from typing import Any, Type

# Configure logging
logger = logging.getLogger(__name__)


def is_valid_enum_value(
    enum_class: Type[Enum], value: Any, strict: bool = True  # noqa: ANN401
) -> bool:
    """Check if the provided value is valid for the given Enum class.

    The function does this by attempting to instantiate an enum member.
    If the value is invalid, a ValueError is raised.
    In strict mode, the value must also match one of the enum member values exactly,
    including the type.

    Args:
        enum_class (Type[Enum]): The Enum class to validate against.
        value (Any): The value to check (can be of any type).
        strict (bool): If True, performs a strict equality check (including type) with Enum values.

    Returns:
    -------
        bool: True if the value is valid for the enum, False otherwise.

    """
    try:
        # Attempt to create an enum member from the value.
        enum_class(value)
        msg = f"'{value}' is treated as a valid value in {enum_class.__name__}."
        logger.info(msg)
        if not strict:
            return True
    except ValueError:
        msg = f"'{value}' is NOT a valid value in {enum_class.__name__}."
        logger.info(msg)
        return False
    except Exception as e:
        msg = f"An unexpected error occurred while checking the enum value. Exception: {e}"
        logger.exception(msg)
        return False

    # Strict check: ensure the value exactly matches one of the enum member values in both value and type.
    values = [e.value for e in enum_class]
    if any(value == v and type(value) is type(v) for v in values):
        return True

    msg = f"Strict check: '{value}' is not an exact match among {values} in {enum_class.__name__}."
    logger.info(msg)
    return False
