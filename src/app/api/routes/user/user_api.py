import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query
from starlette.status import HTTP_200_OK, HTTP_500_INTERNAL_SERVER_ERROR

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


@router.get("/read/{user_id}", response_model=Dict[str, Any])
async def read_user(
    user_id: str,
    wiki_services: WikiManagerServices = Depends(WIKI_MANAGER_FACTORY),
    auth_user: AuthenticatedUser = Depends(AUTHENTICATION_PROVIDER),
):
    try:
        user_data = await wiki_services.user_service.get_user(user_id)
        return ORJSONResponse(
            status_code=HTTP_200_OK,
            content=user_data,
        )
    except ApiException as exc:
        LOGGER.error(f"Error getting user: {exc}")
        return ORJSONResponse(status_code=exc.status_code, content=exc.message)
    except Exception as exc:
        LOGGER.error(f"Unexpected exception: {exc}")
        return ORJSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiException.server_internal_error(),
        )


@router.get("/list", response_model=Dict[str, Any])
async def list_users(
    page: int = Query(default=1, ge=1, alias="page"),
    max_results: int = Query(default=20, ge=1, le=100),
    wiki_services: WikiManagerServices = Depends(WIKI_MANAGER_FACTORY),
    auth_user: AuthenticatedUser = Depends(AUTHENTICATION_PROVIDER),
):
    try:
        users_data = await wiki_services.user_service.get_users(
            page=page,
            max_results=max_results,
            auth_user=auth_user,
        )
        return ORJSONResponse(status_code=HTTP_200_OK, content=users_data)
    except ApiException as exc:
        LOGGER.error(f"Error getting users list: {exc}")
        return ORJSONResponse(status_code=exc.status_code, content=exc.message)
    except Exception as exc:
        LOGGER.error(f"Unexpected exception: {exc}")
        return ORJSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiException.server_internal_error(),
        )
