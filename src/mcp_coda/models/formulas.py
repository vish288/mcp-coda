"""Formula response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Formula(BaseModel):
    """Coda named formula."""

    id: str
    type: str = "formula"
    name: str = ""
    href: str | None = None
    parent: dict | None = None
    value: Any = None
    value_format: dict | None = Field(default=None, alias="valueFormat")
