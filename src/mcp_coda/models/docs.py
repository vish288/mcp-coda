"""Doc response models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .base import Icon


class DocSize(BaseModel):
    """Doc size metrics."""

    total_row_count: int = Field(0, alias="totalRowCount")
    table_and_view_count: int = Field(0, alias="tableAndViewCount")
    page_count: int = Field(0, alias="pageCount")
    over_api_size_limit: bool = Field(False, alias="overApiSizeLimit")


class Doc(BaseModel):
    """Coda doc metadata."""

    id: str
    type: str = "doc"
    name: str = ""
    href: str | None = None
    browser_link: str | None = Field(default=None, alias="browserLink")
    owner: str | None = None
    owner_name: str | None = Field(default=None, alias="ownerName")
    created_at: str | None = Field(default=None, alias="createdAt")
    updated_at: str | None = Field(default=None, alias="updatedAt")
    icon: Icon | None = None
    doc_size: DocSize | None = Field(default=None, alias="docSize")
    source_doc: dict | None = Field(default=None, alias="sourceDoc")
    folder_id: str | None = Field(default=None, alias="folderId")
    workspace_id: str | None = Field(default=None, alias="workspaceId")
    published: dict | None = None
