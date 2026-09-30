from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.wiki.wiki_models import Status


class SearchOptionsDTO(BaseModel):
    page: int = Field(default=1, ge=1)
    max_results: int = Field(default=20, ge=1, le=100)
    order_by: str = Field(default="created_at")
    direction: str = Field(default="DESC")
    state: Optional[Status] = None
    tags: Optional[List[str]] = None
    search: Optional[str] = None
    user_id: Optional[str] = None

    @field_validator("direction")
    def validate_direction(cls, v: str) -> str:
        upper_v = v.upper()
        if upper_v not in ("ASC", "DESC"):
            raise ValueError("Sorting direction must be 'ASC' or 'DESC'.")
        return upper_v

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.max_results
