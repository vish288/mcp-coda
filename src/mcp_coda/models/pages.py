"""Page response models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .base import Icon


class Page(BaseModel):
    """Coda page metadata."""

    id: str
    type: str = "page"
    name: str = ""
    href: str | None = None
    browser_link: str | None = Field(default=None, alias="browserLink")
    subtitle: str | None = None
    icon: Icon | None = None
    image: str | None = None
    parent: dict | None = None
    children: list[dict] | None = None
    content_type: str | None = Field(default=None, alias="contentType")
    created_at: str | None = Field(default=None, alias="createdAt")
    updated_at: str | None = Field(default=None, alias="updatedAt")


class PageContent(BaseModel):
    """Page content response."""

    content: str = ""
    content_format: str = Field("html", alias="contentFormat")
