from __future__ import annotations

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, description="Page number (1-based)")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        return self.per_page


class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int
    page: int
    per_page: int
    has_more: bool

    @classmethod
    def build(cls, items: list[T], total: int, params: PaginationParams) -> PaginatedResponse[T]:
        return cls(
            items=items,
            total=total,
            page=params.page,
            per_page=params.per_page,
            has_more=params.offset + len(items) < total,
        )
