import logging
from typing import List

from fastapi import APIRouter, Depends
from starlette.responses import Response
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.api.dto.wiki.wiki_dto import (
    CategoryResponseDTO,
    CreateCategoryDTO,
    UpdateCategoryDTO,
)
from app.core.exceptions.api_exception import ApiException
from app.core.json.json_response import ORJSONResponse
from app.models.security.auth_user import AuthenticatedUser
from app.security.authentication_provider import AUTHENTICATION_PROVIDER
from app.services.factory.services_factory import (
    WIKI_MANAGER_FACTORY,
    WikiManagerServices,
)

LOGGER = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/create", response_model=CategoryResponseDTO, status_code=HTTP_201_CREATED
)
async def create_category(
    category_request: CreateCategoryDTO,
    wiki_services: WikiManagerServices = Depends(WIKI_MANAGER_FACTORY),
    auth_user: AuthenticatedUser = Depends(AUTHENTICATION_PROVIDER),
):
    try:
        category = await wiki_services.category_service.create_category(
            auth_user, category_request
        )
        return ORJSONResponse(
            status_code=HTTP_201_CREATED,
            content=category.model_dump(),
        )
    except ApiException as exc:
        LOGGER.error(f"Error creating new category: {exc}")
        return ORJSONResponse(status_code=exc.status_code, content=exc.message)
    except Exception as exc:
        LOGGER.error(f"Unexpected exception: {exc}")
        return ORJSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiException.server_internal_error(),
        )


@router.get("/read/{category_id}", response_model=CategoryResponseDTO)
async def read_category(
    category_id: str,
    wiki_services: WikiManagerServices = Depends(WIKI_MANAGER_FACTORY),
    auth_user: AuthenticatedUser = Depends(AUTHENTICATION_PROVIDER),
):
    try:
        category = await wiki_services.category_service.get_category(
            auth_user, category_id
        )
        return ORJSONResponse(
            status_code=HTTP_200_OK,
            content=category.model_dump(),
        )
    except ApiException as exc:
        LOGGER.error(f"Error getting category: {exc}")
        return ORJSONResponse(status_code=exc.status_code, content=exc.message)
    except Exception as exc:
        LOGGER.error(f"Unexpected exception: {exc}")
        return ORJSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiException.server_internal_error(),
        )


@router.get("/list", response_model=List[CategoryResponseDTO])
async def get_all_categories_list(
    index_size: int = 1,
    max_results: int = 20,
    wiki_services: WikiManagerServices = Depends(WIKI_MANAGER_FACTORY),
    auth_user: AuthenticatedUser = Depends(AUTHENTICATION_PROVIDER),
):
    try:
        categories_data = await wiki_services.category_service.get_all_categories(
            auth_user, index_size, max_results
        )
        content_payload = (
            categories_data[0]
            if isinstance(categories_data, tuple)
            else categories_data
        )

        return ORJSONResponse(
            status_code=HTTP_200_OK,
            content=(
                [cat.model_dump() for cat in content_payload]
                if isinstance(content_payload, list)
                else content_payload
            ),
        )
    except ApiException as exc:
        LOGGER.error(f"Error getting categories list: {exc}")
        return ORJSONResponse(status_code=exc.status_code, content=exc.message)
    except Exception as exc:
        LOGGER.error(f"Unexpected exception: {exc}")
        return ORJSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiException.server_internal_error(),
        )


@router.put("/update", status_code=HTTP_204_NO_CONTENT)
async def update_category(
    category_id: str,
    category_request: UpdateCategoryDTO,
    wiki_services: WikiManagerServices = Depends(WIKI_MANAGER_FACTORY),
    auth_user: AuthenticatedUser = Depends(AUTHENTICATION_PROVIDER),
):
    try:
        await wiki_services.category_service.update_category(
            auth_user, category_id, category_request
        )
        return Response(
            status_code=HTTP_204_NO_CONTENT,
        )
    except ApiException as exc:
        LOGGER.error(f"Error updating category: {exc}")
        return ORJSONResponse(status_code=exc.status_code, content=exc.message)
    except Exception as exc:
        LOGGER.error(f"Unexpected exception: {exc}")
        return ORJSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiException.server_internal_error(),
        )


@router.delete("/delete/{category_id}", status_code=HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    wiki_services: WikiManagerServices = Depends(WIKI_MANAGER_FACTORY),
    auth_user: AuthenticatedUser = Depends(AUTHENTICATION_PROVIDER),
):
    try:
        await wiki_services.category_service.delete_category(auth_user, category_id)
        return Response(
            status_code=HTTP_204_NO_CONTENT,
        )
    except ApiException as exc:
        LOGGER.error(f"Error deleting category: {exc}")
        return ORJSONResponse(status_code=exc.status_code, content=exc.message)
    except Exception as exc:
        LOGGER.error(f"Unexpected exception: {exc}")
        return ORJSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiException.server_internal_error(),
        )
