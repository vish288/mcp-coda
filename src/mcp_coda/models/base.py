"""Base models shared across all Coda API responses."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response envelope."""

    items: list[T] = Field(default_factory=list)
    has_more: bool = False
    next_cursor: str | None = None
    total_count: int = 0


class Icon(BaseModel):
    """Coda icon reference."""

    name: str
    type: str = "name"


class Person(BaseModel):
    """Coda person/user reference."""

    email: str | None = None
    name: str | None = None


class MutationStatus(BaseModel):
    """Status of an async mutation."""

    completed: bool
    request_id: str = Field(alias="requestId")
    warning: str | None = None


class LinkedResource(BaseModel):
    """A resource reference with ID, type, and optional link."""

    id: str
    type: str
    name: str | None = None
    href: str | None = None
    browser_link: str | None = Field(default=None, alias="browserLink")


class ApiLink(BaseModel):
    """API link reference."""

    rel: str | None = None
    href: str
    method: str | None = None
    params: dict[str, Any] | None = None
