"""Table and column response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Column(BaseModel):
    """Coda table column."""

    id: str
    type: str = "column"
    name: str = ""
    href: str | None = None
    display: bool = False
    calculated: bool = False
    formula: str | None = None
    default_value: str | None = Field(default=None, alias="defaultValue")
    format: dict[str, Any] | None = None


class Table(BaseModel):
    """Coda table metadata."""

    id: str
    type: str = "table"
    name: str = ""
    href: str | None = None
    browser_link: str | None = Field(default=None, alias="browserLink")
    parent: dict | None = None
    table_type: str | None = Field(default=None, alias="tableType")
    display_column: dict | None = Field(default=None, alias="displayColumn")
    row_count: int = Field(0, alias="rowCount")
    created_at: str | None = Field(default=None, alias="createdAt")
    updated_at: str | None = Field(default=None, alias="updatedAt")
    sort: list[dict] | None = None
    filter: dict | None = None
    layout: str | None = None
