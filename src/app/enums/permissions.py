from enum import Enum


class PermissionType(Enum):
    """Types of permissions that can be granted on blueprint."""

    READ = "read"
    WRITE = "write"


class PermissionEntityType(Enum):
    """Types of entities that can be granted permissions."""

    USER = "user"
    WORKSPACE = "workspace"