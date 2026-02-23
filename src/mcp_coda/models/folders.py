"""Folder response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Folder(BaseModel):
    """Coda folder."""

    id: str
    type: str = "folder"
    name: str = ""
    href: str | None = None
    browser_link: str | None = Field(default=None, alias="browserLink")
    parent_folder_id: str | None = Field(default=None, alias="parentFolderId")
    owner: str | None = None
    created_at: str | None = Field(default=None, alias="createdAt")
    updated_at: str | None = Field(default=None, alias="updatedAt")
