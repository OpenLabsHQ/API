from enum import Enum


class WorkspaceRole(Enum):
    """Roles that a user can have within a workspace."""

    ADMIN = "admin"  # Can manage workspace and members
    MEMBER = "member"  # Regular workspace member