from enum import Enum

from src.app.validators.enums import is_valid_enum_value


class Color(Enum):
    """A simple string-based enum for colors."""

    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class Priority(Enum):
    """An integer-based enum for priority levels."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


# ============================
# Tests for the non-strict branch
# ============================


def test_valid_color_red_non_strict() -> None:
    """Test that 'red' is valid for Color enum in non-strict mode."""
    assert is_valid_enum_value(Color, "red", strict=False) is True


def test_invalid_color_yellow_non_strict() -> None:
    """Test that 'yellow' is not valid for Color enum in non-strict mode."""
    assert is_valid_enum_value(Color, "yellow", strict=False) is False


# ============================
# Tests for the strict branch
# ============================


def test_color_strict_valid() -> None:
    """Test that 'red' is valid for Color enum in strict mode."""
    assert is_valid_enum_value(Color, "red", strict=True) is True


def test_color_strict_invalid_type() -> None:
    """Test that passing an integer to a string-based enum (Color) is invalid in strict mode.

    Even if the enum conversion might succeed in non-strict mode, the type mismatch should fail.
    """
    assert is_valid_enum_value(Color, 1, strict=True) is False


def test_priority_strict_int_valid() -> None:
    """Test that the integer 1 is valid for Priority enum in strict mode."""
    assert is_valid_enum_value(Priority, 1, strict=True) is True


def test_priority_strict_float_invalid() -> None:
    """Test that passing a float (1.0) to an integer-based enum (Priority) is invalid in strict mode, even though non-strict mode would accept it."""
    assert is_valid_enum_value(Priority, 1.0, strict=True) is False


def test_priority_non_strict_float_valid() -> None:
    """Test that passing a float (1.0) to an integer-based enum (Priority) is valid in non-strict mode.

    This demonstrates that non-strict mode is more lenient with type conversion.
    """
    assert is_valid_enum_value(Priority, 1.0, strict=False) is True


def test_priority_strict_string_invalid() -> None:
    """Test that passing a numeric string ('1') to an integer-based enum (Priority) is invalid in strict mode."""
    assert is_valid_enum_value(Priority, "1", strict=True) is False


def test_priority_strict_boolean_invalid() -> None:
    """Test that passing a boolean value (True) to an integer-based enum (Priority) is invalid in strict mode."""
    assert is_valid_enum_value(Priority, True, strict=True) is False


# ============================
# Additional Tests for Robustness
# ============================


def test_invalid_value_type_error() -> None:
    """Test that a completely unrelated type (e.g., list) is not considered a valid enum value, regardless of strictness."""
    assert is_valid_enum_value(Color, [1, 2, 3], strict=True) is False
    assert is_valid_enum_value(Color, [1, 2, 3], strict=False) is False


def test_none_value() -> None:
    """Test that None is not considered a valid value for any enum, regardless of strictness."""
    assert is_valid_enum_value(Color, None, strict=True) is False
    assert is_valid_enum_value(Priority, None, strict=False) is False
