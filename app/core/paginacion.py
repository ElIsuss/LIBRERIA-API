from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(cls, *, items: list[T], total: int, page: int, size: int) -> "Page[T]":
        if total == 0:
            pages = 1
        else:
            pages = max(1, (total + size - 1) // size)

        if page > pages:
            raise ValueError("page exceeds the available pages")

        return cls(items=items, total=total, page=page, size=size, pages=pages)
