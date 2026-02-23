"""Permission and ACL response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Principal(BaseModel):
    """A user or domain principal."""

    type: str = ""
    email: str | None = None
    domain: str | None = None
    name: str | None = None


class Permission(BaseModel):
    """Coda doc permission entry."""

    id: str
    principal: Principal | None = None
    access: str = ""
    inherit_only: bool = Field(False, alias="inheritOnly")


class SharingMetadata(BaseModel):
    """Doc sharing metadata."""

    can_share: bool = Field(False, alias="canShare")
    can_share_with_org: bool = Field(False, alias="canShareWithOrg")


class AclSettings(BaseModel):
    """Doc ACL settings."""

    allow_editors_to_change_permissions: bool = Field(
        False, alias="allowEditorsToChangePermissions"
    )
    allow_copying: bool = Field(False, alias="allowCopying")
    allow_view_all_users: bool = Field(False, alias="allowViewAllUsers")
