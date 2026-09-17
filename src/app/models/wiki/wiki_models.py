from enum import Enum
from typing import List, Optional

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

from app.models.common.audit import AuditMixin


class Status(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    PENDING = "PENDING"
    CORRECTION_REQUESTED = "CORRECTION_REQUESTED"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"


class ReactionType(str, Enum):
    LIKE = "LIKE"
    DISLIKE = "DISLIKE"


class ArticleCategoryLink(SQLModel, table=True):
    __tablename__ = "article_categories"  # type: ignore
    article_id: str = Field(foreign_key="articles.article_id", primary_key=True)
    category_id: str = Field(foreign_key="categories.category_id", primary_key=True)


class ArticleMediaLink(SQLModel, table=True):
    __tablename__ = "article_medias_gallery"  # type: ignore
    article_id: str = Field(foreign_key="articles.article_id", primary_key=True)
    media_id: str = Field(foreign_key="medias.media_id", primary_key=True)


class Category(AuditMixin, table=True):
    __tablename__ = "categories"  # type: ignore
    category_id: str = Field(unique=True, index=True, nullable=False, primary_key=True)
    title: str = Field(index=True, unique=True, nullable=False)
    description: Optional[str] = Field(default=None, nullable=True)
    articles: List["Article"] = Relationship(
        back_populates="categories", link_model=ArticleCategoryLink
    )


class Media(AuditMixin, table=True):
    __tablename__ = "medias"  # type: ignore
    media_id: str = Field(
        max_length=40, unique=True, index=True, nullable=False, primary_key=True
    )
    file_name: str = Field(max_length=255, nullable=False)
    file_type: str = Field(max_length=255, nullable=False)
    url: str = Field(nullable=False)


class Comment(AuditMixin, table=True):
    __tablename__ = "comments"  # type: ignore
    comment_id: str = Field(
        max_length=40, unique=True, nullable=False, primary_key=True
    )
    content: str = Field(max_length=128, nullable=False)
    is_deleted: bool = Field(default=False, nullable=False, exclude=True)
    article_id: str = Field(foreign_key="articles.article_id", nullable=False)
    article: "Article" = Relationship(back_populates="comments")


class ArticleReaction(AuditMixin, table=True):
    __tablename__ = "article_reactions"  # type: ignore
    reaction_id: str = Field(
        max_length=40, unique=True, nullable=False, primary_key=True
    )
    article_id: str = Field(
        max_length=40, foreign_key="articles.article_id", index=True, nullable=False
    )
    user_id: str = Field(max_length=55, index=True, nullable=False)
    reaction: ReactionType = Field(index=True, nullable=False)
    __table_args__ = (
        UniqueConstraint(
            "article_id", "user_id", name="uq_article_reactions_article_user"
        ),
    )
    article: "Article" = Relationship(back_populates="reactions")


class Article(AuditMixin, table=True):
    __tablename__ = "articles"  # type: ignore
    article_id: str = Field(
        max_length=40, unique=True, index=True, primary_key=True, nullable=False
    )
    title: str = Field(index=True, nullable=False)
    content: str = Field(nullable=False)
    tags: Optional[List[str]] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    sources: Optional[List[str]] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    state: Status = Field(index=True, nullable=False)
    likes: int = Field(default=0, nullable=False)
    dislikes: int = Field(default=0, nullable=False)
    is_deleted: bool = Field(default=False, nullable=False, exclude=True)
    user_id: str = Field(index=True, nullable=False)
    admin_review: Optional[str] = Field(default=None, index=True, nullable=True)
    cover_image_id: Optional[str] = Field(
        default=None, foreign_key="medias.media_id", nullable=True
    )

    categories: List[Category] = Relationship(
        back_populates="articles", link_model=ArticleCategoryLink
    )
    article_medias_gallery: List[Media] = Relationship(link_model=ArticleMediaLink)
    comments: List[Comment] = Relationship(
        back_populates="article",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    reactions: List[ArticleReaction] = Relationship(
        back_populates="article",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
