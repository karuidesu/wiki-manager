import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from starlette.status import HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from app.api.dto.wiki.wiki_dto import (
    CategoryResponseDTO,
    CreateCategoryDTO,
    UpdateCategoryDTO,
)
from app.core.exceptions.api_exception import ApiErrorsCode, ApiException
from app.models.security.auth_user import AuthenticatedUser
from app.models.wiki import Category
from app.security.access_granter import has_any_roles
from app.security.api_roles import ApiRoles
from app.storage.rds.datastore.interfaces.category import ICategory

LOGGER = logging.getLogger(__name__)


class CategoryService:
    def __init__(self, category_store: ICategory):
        self._category_store = category_store

    @has_any_roles(
        logger=LOGGER,
        resource="CATEGORY",
        roles=[ApiRoles.MANAGER, ApiRoles.DIRECTOR],
    )
    async def create_category(
        self, auth_user: AuthenticatedUser, category_request: CreateCategoryDTO
    ) -> Dict[str, Any]:
        existing_category = await self._category_store.get_category_by_title(
            title=category_request.title
        )
        if existing_category:
            raise ApiException(
                status_code=HTTP_409_CONFLICT,
                error_code=ApiErrorsCode.CATEGORY_ALREADY_EXISTS,
                message=(
                    f"Category with title '{category_request.title}' already exists."
                ),
            )

        now = datetime.now(timezone.utc)
        category_model = Category(
            category_id=str(uuid.uuid4()),
            title=category_request.title,
            description=category_request.description,
            created_by=auth_user.user_id,
            created_at=now,
            updated_by=None,
            updated_at=now,
            version=1,
        )

        category = await self._category_store.create_category(category=category_model)
        return {
            "message": "Category created successfully.",
            "category": category,
        }

    @has_any_roles(
        logger=LOGGER,
        resource="CATEGORY",
        roles=[ApiRoles.MANAGER, ApiRoles.DIRECTOR, ApiRoles.EMPLOYEE],
    )
    async def get_category(
        self, auth_user: AuthenticatedUser, category_id: str
    ) -> Optional[CategoryResponseDTO]:
        category = await self._category_store.get_category(category_id=category_id)
        if not category:
            raise ApiException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ApiErrorsCode.CATEGORY_NOT_FOUND,
                message=f"Category with id '{category_id}' not found.",
            )
        return category

    @has_any_roles(
        logger=LOGGER,
        resource="CATEGORY",
        roles=[ApiRoles.MANAGER, ApiRoles.DIRECTOR, ApiRoles.EMPLOYEE],
    )
    async def get_all_categories(
        self,
        auth_user: AuthenticatedUser,
        index_size: int = 1,
        max_result: int = 20,
    ) -> Tuple[list[CategoryResponseDTO], int]:
        return await self._category_store.list_categories(
            index=index_size, limit=max_result
        )

    @has_any_roles(
        logger=LOGGER,
        resource="CATEGORY",
        roles=[ApiRoles.DIRECTOR, ApiRoles.MANAGER],
    )
    async def update_category(
        self,
        auth_user: AuthenticatedUser,
        category_id: str,
        category_request: UpdateCategoryDTO,
    ) -> Dict[str, Any]:
        current_category_dto = await self._category_store.get_category(
            category_id=category_id
        )
        if not current_category_dto:
            raise ApiException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ApiErrorsCode.CATEGORY_NOT_FOUND,
                message=f"Category with id '{category_id}' not found.",
            )

        if (
            category_request.title
            and category_request.title != current_category_dto.title
        ):
            title_conflict = await self._category_store.get_category_by_title(
                title=category_request.title
            )
            if title_conflict:
                raise ApiException(
                    status_code=HTTP_409_CONFLICT,
                    error_code=ApiErrorsCode.CATEGORY_ALREADY_EXISTS,
                    message=(
                        f"Category with title '{category_request.title}'"
                        + " already exists."
                    ),
                )

        now = datetime.now(timezone.utc)
        updated_model = Category(
            category_id=current_category_dto.category_id,
            title=(
                category_request.title
                if category_request.title is not None
                else current_category_dto.title
            ),
            description=(
                category_request.description
                if category_request.description is not None
                else current_category_dto.description
            ),
            created_by=current_category_dto.created_by,
            created_at=current_category_dto.created_at,
            updated_by=auth_user.user_id,
            updated_at=now,
            version=current_category_dto.version,
        )

        category = await self._category_store.update_category(
            category=updated_model, category_id=category_id
        )
        return {
            "message": "Category updated successfully.",
            "category": category,
        }

    @has_any_roles(
        logger=LOGGER,
        resource="CATEGORY",
        roles=[ApiRoles.DIRECTOR, ApiRoles.MANAGER],
    )
    async def delete_category(
        self, auth_user: AuthenticatedUser, category_id: str
    ) -> Dict[str, str]:
        existing_category = await self._category_store.get_category(
            category_id=category_id
        )
        if not existing_category:
            raise ApiException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ApiErrorsCode.CATEGORY_NOT_FOUND,
                message=f"Category with id '{category_id}' not found.",
            )

        await self._category_store.delete_category(category_id=category_id)
        return {"message": "Category deleted successfully."}
