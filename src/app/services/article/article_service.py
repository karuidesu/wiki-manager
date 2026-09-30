import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)

from app.core.exceptions.api_exception import ApiErrorsCode, ApiException
from app.models.security.auth_user import AuthenticatedUser
from app.models.wiki.wiki_models import (
    Article,
    ArticleReaction,
    Comment,
    ReactionType,
    Status,
)
from app.security.api_roles import ApiRoles
from app.storage.rds.datastore.interfaces.article import IArticle
from app.storage.rds.datastore.interfaces.category import ICategory
from app.storage.rds.datastore.interfaces.media import IMedia
from app.storage.rds.dto.search_options import SearchOptionsDTO

LOGGER = logging.getLogger(__name__)


class ArticleService:
    def __init__(
        self,
        article_store: IArticle,
        category_store: ICategory,
        media_store: IMedia,
    ):
        self._article_store = article_store
        self._category_store = category_store
        self._media_store = media_store

    async def create_article(
        self, payload: dict, auth_user: AuthenticatedUser
    ) -> Article:
        state = payload.get("state", Status.SUBMITTED)
        state_val = state.value if isinstance(state, Status) else state

        if state_val not in [Status.DRAFT.value, Status.SUBMITTED.value]:
            raise ApiException(
                status_code=HTTP_400_BAD_REQUEST,
                error_code=ApiErrorsCode.INVALID_ARTICLE_STATE,
                message="An article can only be created in DRAFT or SUBMITTED state.",
            )

        article_id = str(uuid.uuid4())

        new_article = Article(
            article_id=article_id,
            title=payload["title"],
            content=payload["content"],
            tags=payload.get("tags", []),
            sources=payload.get("sources", []),
            state=state,
            user_id=auth_user.user_id,
            cover_image_id=payload.get("cover_image_id"),
            created_by=auth_user.user_id,
            created_at=datetime.now(timezone.utc),
            version=1,
            is_deleted=False,
        )

        try:
            category_ids = payload.get("categories", [])
            if category_ids:
                categories = await self._category_store.get_categories_by_ids(
                    category_ids
                )
                new_article.categories = categories

            media_ids = payload.get("media_ids", [])
            if media_ids:
                medias = await self._media_store.get_medias_by_ids(media_ids)
                new_article.article_medias_gallery = medias

            created_article = await self._article_store.create_article(new_article)
            LOGGER.info(
                f"Article {article_id} created successfully by {auth_user.user_id}."
            )
            return created_article

        except Exception as exc:
            LOGGER.error("Error while creating article: %s", str(exc))
            raise exc

    async def get_article(self, article_id: str) -> Article:
        article = await self._article_store.get_article(article_id)
        if article is None or article.is_deleted:
            raise ApiException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ApiErrorsCode.ARTICLE_NOT_FOUND,
                message="ARTICLE_NOT_FOUND",
            )
        return article

    async def get_all_articles(
        self,
        page: int = 1,
        max_results: int = 20,
        order_by: str = "created_at",
        direction: str = "DESC",
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        options = SearchOptionsDTO(
            page=page,
            max_results=max_results,
            order_by=order_by,
            direction=direction,
            state=Status.PUBLISHED,
            tags=tags,
            search=search,
        )
        try:
            items, total = await self._article_store.search_articles(options)
        except ValueError as err:
            raise ApiException(
                status_code=HTTP_400_BAD_REQUEST,
                error_code=ApiErrorsCode.INVALID_SORT_FIELD,
                message=str(err),
            )

        return {
            "items": [
                article.model_dump() if hasattr(article, "model_dump") else article
                for article in items
            ],
            "total": total,
            "page": page,
            "max_results": max_results,
            "total_pages": (total + max_results - 1) // max_results if total > 0 else 0,
        }

    async def get_admin_all_articles(
        self,
        auth_user: AuthenticatedUser,
        page: int = 1,
        max_results: int = 20,
        order_by: str = "created_at",
        direction: str = "DESC",
        state: Optional[Status] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        author_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        user_roles = getattr(auth_user, "roles", [])
        is_reviewer = any(
            role in user_roles for role in [ApiRoles.MANAGER, ApiRoles.DIRECTOR]
        )
        if not is_reviewer:
            raise ApiException(
                status_code=HTTP_403_FORBIDDEN,
                error_code=ApiErrorsCode.FORBIDDEN,
                message="Access denied. Reviewer role required.",
            )

        options = SearchOptionsDTO(
            page=page,
            max_results=max_results,
            order_by=order_by,
            direction=direction,
            state=state,
            tags=tags,
            search=search,
            user_id=author_id,
        )
        try:
            items, total = await self._article_store.search_articles(options)
        except ValueError as err:
            raise ApiException(
                status_code=HTTP_400_BAD_REQUEST,
                error_code=ApiErrorsCode.INVALID_SORT_FIELD,
                message=str(err),
            )

        return {
            "items": [
                article.model_dump() if hasattr(article, "model_dump") else article
                for article in items
            ],
            "total": total,
            "page": page,
            "max_results": max_results,
            "total_pages": (total + max_results - 1) // max_results if total > 0 else 0,
        }

    async def update_article(
        self, article_id: str, payload: dict, auth_user: AuthenticatedUser
    ) -> Article:
        article = await self.get_article(article_id)

        if article.user_id != auth_user.user_id:
            raise ApiException(
                status_code=HTTP_403_FORBIDDEN,
                error_code=ApiErrorsCode.FORBIDDEN,
                message="You are not the author of this article.",
            )

        current_state = (
            article.state.value if isinstance(article.state, Status) else article.state
        )

        if current_state not in [Status.DRAFT.value, Status.CORRECTION_REQUESTED.value]:
            raise ApiException(
                status_code=HTTP_400_BAD_REQUEST,
                error_code=ApiErrorsCode.INVALID_ARTICLE_TRANSITION,
                message=f"Cannot resubmit article with state '{current_state}'.",
            )

        article.title = payload.get("title", article.title)
        article.content = payload.get("content", article.content)
        article.tags = payload.get("tags", article.tags)
        article.sources = payload.get("sources", article.sources)
        article.cover_image_id = payload.get("cover_image_id", article.cover_image_id)

        article.state = Status.SUBMITTED
        article.updated_by = auth_user.user_id
        article.updated_at = datetime.now(timezone.utc)

        category_ids = payload.get("categories")
        if category_ids is not None:
            categories = await self._category_store.get_categories_by_ids(category_ids)
            article.categories = categories

        media_ids = payload.get("media_ids")
        if media_ids is not None:
            medias = await self._media_store.get_medias_by_ids(media_ids)
            article.article_medias_gallery = medias

        return await self._article_store.update_article(article)

    async def request_correction(
        self, article_id: str, admin_review: str, admin_user: AuthenticatedUser
    ) -> Article:
        article = await self.get_article(article_id)

        if article.state not in [Status.SUBMITTED, Status.PENDING]:
            raise ApiException(
                status_code=HTTP_400_BAD_REQUEST,
                error_code=ApiErrorsCode.INVALID_ARTICLE_TRANSITION,
                message=(
                    "Corrections can only be requested for "
                    "submitted or pending articles."
                ),
            )

        article.state = Status.CORRECTION_REQUESTED
        article.admin_review = admin_review
        article.updated_by = admin_user.user_id
        article.updated_at = datetime.now(timezone.utc)

        return await self._article_store.update_article(article)

    async def publish(self, article_id: str, admin_user: AuthenticatedUser) -> Article:
        article = await self.get_article(article_id)

        current_state = (
            article.state.value if isinstance(article.state, Status) else article.state
        )

        if current_state not in [Status.SUBMITTED.value, Status.APPROVED.value]:
            raise ApiException(
                status_code=HTTP_400_BAD_REQUEST,
                error_code=ApiErrorsCode.INVALID_ARTICLE_TRANSITION,
                message="Article is not in a publishable state.",
            )

        article.state = Status.PUBLISHED
        article.updated_by = admin_user.user_id
        article.updated_at = datetime.now(timezone.utc)

        return await self._article_store.update_article(article)

    async def delete_article(self, article_id: str, auth_user: AuthenticatedUser):
        LOGGER.info(f"Soft deleting article {article_id} by user {auth_user.user_id}")
        try:
            article = await self.get_article(article_id)

            if article.user_id != auth_user.user_id:
                raise ApiException(
                    status_code=HTTP_403_FORBIDDEN,
                    error_code=ApiErrorsCode.FORBIDDEN,
                    message="Operation not allowed.",
                )

            article.is_deleted = True
            article.updated_by = auth_user.user_id
            article.updated_at = datetime.now(timezone.utc)

            await self._article_store.update_article(article)
            LOGGER.info(f"Soft deleted article: {article_id}")

        except Exception as exc:
            LOGGER.error("Error while deleting article: %s", str(exc))
            raise exc

    async def like_article(self, article_id: str, auth_user: AuthenticatedUser):
        article = await self.get_article(article_id)
        existing = await self._article_store.get_reaction(
            article.article_id, auth_user.user_id
        )

        if existing:
            if existing.reaction == ReactionType.LIKE:
                return existing
            existing.reaction = ReactionType.LIKE
            existing.updated_by = auth_user.user_id
            existing.updated_at = datetime.now(timezone.utc)
            return await self._article_store.save_reaction(
                existing, like=1, dislike=-1, is_update=True
            )

        reaction = ArticleReaction(
            reaction_id=str(uuid.uuid4()),
            article_id=article.article_id,
            user_id=auth_user.user_id,
            reaction=ReactionType.LIKE,
            created_by=auth_user.user_id,
            created_at=datetime.now(timezone.utc),
            version=1,
        )
        return await self._article_store.save_reaction(reaction, like=1, dislike=0)

    async def dislike_article(self, article_id: str, auth_user: AuthenticatedUser):
        article = await self.get_article(article_id)
        existing = await self._article_store.get_reaction(
            article.article_id, auth_user.user_id
        )

        if existing:
            if existing.reaction == ReactionType.DISLIKE:
                return existing
            existing.reaction = ReactionType.DISLIKE
            existing.updated_by = auth_user.user_id
            existing.updated_at = datetime.now(timezone.utc)
            return await self._article_store.save_reaction(
                existing, like=-1, dislike=1, is_update=True
            )

        reaction = ArticleReaction(
            reaction_id=str(uuid.uuid4()),
            article_id=article.article_id,
            user_id=auth_user.user_id,
            reaction=ReactionType.DISLIKE,
            created_by=auth_user.user_id,
            created_at=datetime.now(timezone.utc),
            version=1,
        )
        return await self._article_store.save_reaction(reaction, like=0, dislike=1)

    async def cancel_reaction(
        self, article_id: str, auth_user: AuthenticatedUser
    ) -> None:
        article = await self.get_article(article_id)
        existing = await self._article_store.get_reaction(
            article.article_id, auth_user.user_id
        )
        if not existing:
            return

        like = -1 if existing.reaction == ReactionType.LIKE else 0
        dislike = -1 if existing.reaction == ReactionType.DISLIKE else 0

        await self._article_store.cancel_reaction(
            reaction=existing,
            like=like,
            dislike=dislike,
        )

    async def load_reactions(
        self,
        article_id: str,
        page_size: int = 1,
        max_result: int = 20,
        direction: str = "DESC",
    ) -> dict:
        await self.get_article(article_id)
        reactions = await self._article_store.load_reactions(
            article_id=article_id,
            page_index=page_size,
            max_result=max_result,
            direction=direction,
        )
        total_count = await self._article_store.count_reactions(article_id)
        return {
            "total": total_count,
            "page_size": page_size,
            "max_result": max_result,
            "reactions": [
                r.model_dump() if hasattr(r, "model_dump") else r for r in reactions
            ],
        }

    async def add_comment(
        self, article_id: str, payload: dict, auth_user: AuthenticatedUser
    ):
        article = await self.get_article(article_id)
        comment = Comment(
            comment_id=str(uuid.uuid4()),
            article_id=article.article_id,
            created_by=auth_user.user_id,
            content=payload["content"],
            created_at=datetime.now(timezone.utc),
            is_deleted=False,
            version=1,
        )
        return await self._article_store.add_comment(comment)

    async def load_comments(
        self,
        article_id: str,
        page_size: int = 1,
        max_result: int = 20,
        direction: str = "DESC",
    ) -> dict:
        await self.get_article(article_id)
        comments = await self._article_store.load_comments(
            article_id=article_id,
            page_index=page_size,
            max_result=max_result,
            direction=direction,
        )
        total_count = await self._article_store.count_comments(article_id)
        return {
            "total": total_count,
            "page_size": page_size,
            "max_result": max_result,
            "comments": [
                c.model_dump() if hasattr(c, "model_dump") else c for c in comments
            ],
        }

    async def delete_comment(
        self, comment_id: str, auth_user: AuthenticatedUser
    ) -> None:
        comment = await self._article_store.get_comment(comment_id)
        if not comment or comment.is_deleted:
            raise ApiException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ApiErrorsCode.COMMENT_NOT_FOUND,
                message="Comment not found.",
            )

        comment_owner = getattr(comment, "created_by", None)
        user_roles = getattr(auth_user, "roles", [])

        is_admin = any(
            role in user_roles for role in [ApiRoles.MANAGER, ApiRoles.DIRECTOR]
        )
        if comment_owner != auth_user.user_id and not is_admin:
            raise ApiException(
                status_code=HTTP_403_FORBIDDEN,
                error_code=ApiErrorsCode.FORBIDDEN,
                message="Operation not allowed.",
            )

        comment.is_deleted = True
        comment.updated_by = auth_user.user_id
        comment.updated_at = datetime.now(timezone.utc)
        await self._article_store.update_comment(comment)
