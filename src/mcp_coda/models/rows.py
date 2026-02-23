"""Row response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Row(BaseModel):
    """Coda table row."""

    id: str
    type: str = "row"
    name: str = ""
    href: str | None = None
    browser_link: str | None = Field(default=None, alias="browserLink")
    index: int = 0
    values: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = Field(default=None, alias="createdAt")
    updated_at: str | None = Field(default=None, alias="updatedAt")
