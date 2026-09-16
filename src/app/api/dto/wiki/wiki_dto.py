from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, constr

id_max_40 = constr(min_length=1, max_length=40, strip_whitespace=True)
non_empty_string = constr(min_length=1, strip_whitespace=True)
comment_str = constr(min_length=1, max_length=128, strip_whitespace=True)


class CreateCategoryDTO(BaseModel):
    title: non_empty_string = Field(...)
    description: Optional[str] = Field(None)


class UpdateCategoryDTO(BaseModel):
    title: Optional[non_empty_string] = Field(None)
    description: Optional[str] = Field(None)


class CategoryResponseDTO(BaseModel):
    category_id: str = Field(...)
    title: str = Field(...)
    description: Optional[str] = Field(None)
    created_by: str = Field(...)
    created_at: datetime = Field(...)
    updated_by: Optional[str] = Field(None)
    updated_at: Optional[datetime] = Field(None)
    version: int = Field(...)

    model_config = ConfigDict(from_attributes=True)


class CreateArticleDTO(BaseModel):
    title: non_empty_string = Field(...)
    content: str = Field(...)
    categories: Optional[list[str]] = Field(None)
    tags: Optional[list[str]] = Field(None)
    sources: Optional[list[str]] = Field(None)


class UpdateArticleDTO(BaseModel):
    title: Optional[non_empty_string] = Field(None)
    content: Optional[str] = Field(None)
    categories: Optional[list[str]] = Field(None)
    tags: Optional[list[str]] = Field(None)
    sources: Optional[list[str]] = Field(None)


class RequestCorrectionDTO(BaseModel):
    admin_review: str = Field(...)


class ArticleResponseDTO(BaseModel):
    article_id: str = Field(...)
    title: str = Field(...)
    content: str = Field(...)
    categories: List[CategoryResponseDTO] = []
    tags: List[str] = []
    sources: List[str] = []
    created_by: str = Field(...)
    created_at: datetime = Field(...)
    updated_by: Optional[str] = Field(None)
    updated_at: Optional[datetime] = Field(None)
    version: int = Field(...)

    model_config = ConfigDict(from_attributes=True)


class AddCommentDTO(BaseModel):
    content: comment_str = Field(...)
