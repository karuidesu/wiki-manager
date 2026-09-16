import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends
from starlette.responses import Response
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.api.dto.wiki.wiki_dto import (
    AddCommentDTO,
    ArticleResponseDTO,
    CreateArticleDTO,
    RequestCorrectionDTO,
    UpdateArticleDTO,
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


@router.post("/create", response_model=ArticleResponseDTO, status_code=HTTP_201_CREATED)
async def create_article(
    article_request: CreateArticleDTO,
    wiki_services: WikiManagerServices = Depends(WIKI_MANAGER_FACTORY),
    auth_user: AuthenticatedUser = Depends(AUTHENTICATION_PROVIDER),
):
    try:
        article = await wiki_services.article_service.create_article(
            article_request.model_dump(), auth_user
        )
        return ORJSONResponse(
            status_code=HTTP_201_CREATED,
            content=(
                article.model_dump() if hasattr(article, "model_dump") else article
            ),
        )
    except ApiException as exc:
        LOGGER.error(f"Error creating new article: {exc}")
        return ORJSONResponse(status_code=exc.status_code, content=exc.message)
    except Exception as exc:
        LOGGER.error(f"Unexpected exception: {exc}")
        return ORJSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiException.server_internal_error(),
        )


@router.get("/read/{article_id}", response_model=ArticleResponseDTO)
async def read_article(
    article_id: str,
    wiki_services: WikiManagerServices = Depends(WIKI_MANAGER_FACTORY),
    auth_user: AuthenticatedUser = Depends(AUTHENTICATION_PROVIDER),
):
    try:
        article = await wiki_services.article_service.get_article(article_id)
        return ORJSONResponse(
            status_code=HTTP_200_OK,
            content=(
                article.model_dump() if hasattr(article, "model_dump") else article
            ),
        )
    except ApiException as exc:
        LOGGER.error(f"Error getting article: {exc}")
        return ORJSONResponse(status_code=exc.status_code, content=exc.message)
    except Exception as exc:
        LOGGER.error(f"Unexpected exception: {exc}")
        return ORJSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiException.server_internal_error(),
        )


@router.get("/list", response_model=Dict[str, Any])
async def get_all_articles(
    page_size: int = 1,
    max_results: int = 20,
    direction: str = "DESC",
    wiki_services: WikiManagerServices = Depends(WIKI_MANAGER_FACTORY),
    auth_user: AuthenticatedUser = Depends(AUTHENTICATION_PROVIDER),
):
    try:
        articles_data = await wiki_services.article_service.get_all_articles(
            page_size=page_size, max_result=max_results, direction=direction
        )
        return ORJSONResponse(
            status_code=HTTP_200_OK,
            content=articles_data,
        )
    except ApiException as exc:
        LOGGER.error(f"Error getting articles list: {exc}")
        return ORJSONResponse(status_code=exc.status_code, content=exc.message)
    except Exception as exc:
        LOGGER.error(f"Unexpected exception: {exc}")
        return ORJSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiException.server_internal_error(),
        )


@router.put("/update/{article_id}", response_model=ArticleResponseDTO)
async def update_article(
    article_id: str,
    article_request: UpdateArticleDTO,
    wiki_services: WikiManagerServices = Depends(WIKI_MANAGER_FACTORY),
    auth_user: AuthenticatedUser = Depends(AUTHENTICATION_PROVIDER),
):
    try:
        article = await wiki_services.article_service.update_article(
            article_id, article_request.model_dump(exclude_unset=True), auth_user
        )
        return ORJSONResponse(
            status_code=HTTP_200_OK,
            content=(
                article.model_dump() if hasattr(article, "model_dump") else article
            ),
        )
    except ApiException as exc:
        LOGGER.error(f"Error resubmitting article: {exc}")
        return ORJSONResponse(status_code=exc.status_code, content=exc.message)
    except Exception as exc:
        LOGGER.error(f"Unexpected exception: {exc}")
        return ORJSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiException.server_internal_error(),
        )


@router.put("/request-correction/{article_id}", response_model=ArticleResponseDTO)
async def request_correction_article(
    article_id: str,
    request_dto: RequestCorrectionDTO,
    wiki_services: WikiManagerServices = Depends(WIKI_MANAGER_FACTORY),
    auth_user: AuthenticatedUser = Depends(AUTHENTICATION_PROVIDER),
):
    try:
        article = await wiki_services.article_service.request_correction(
            article_id, request_dto.admin_review, auth_user
        )
        return ORJSONResponse(
            status_code=HTTP_200_OK,
            content=(
                article.model_dump() if hasattr(article, "model_dump") else article
            ),
        )
    except ApiException as exc:
        LOGGER.error(f"Error requesting correction: {exc}")
        return ORJSONResponse(status_code=exc.status_code, content=exc.message)
    except Exception as exc:
        LOGGER.error(f"Unexpected exception: {exc}")
        return ORJSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiException.server_internal_error(),
        )


@router.put("/publish/{article_id}", response_model=ArticleResponseDTO)
async def publish_article(
    article_id: str,
    wiki_services: WikiManagerServices = Depends(WIKI_MANAGER_FACTORY),
    auth_user: AuthenticatedUser = Depends(AUTHENTICATION_PROVIDER),
):
    try:
        article = await wiki_services.article_service.publish(article_id, auth_user)
        return ORJSONResponse(
            status_code=HTTP_200_OK,
            content=(
                article.model_dump() if hasattr(article, "model_dump") else article
            ),
        )
    except ApiException as exc:
        LOGGER.error(f"Error publishing article: {exc}")
        return ORJSONResponse(status_code=exc.status_code, content=exc.message)
    except Exception as exc:
        LOGGER.error(f"Unexpected exception: {exc}")
        return ORJSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiException.server_internal_error(),
        )


@router.delete("/delete/{article_id}", status_code=HTTP_204_NO_CONTENT)
async def delete_article(
    article_id: str,
    wiki_services: WikiManagerServices = Depends(WIKI_MANAGER_FACTORY),
    auth_user: AuthenticatedUser = Depends(AUTHENTICATION_PROVIDER),
):
    try:
        await wiki_services.article_service.delete_article(article_id, auth_user)
        return Response(status_code=HTTP_204_NO_CONTENT)
    except ApiException as exc:
        LOGGER.error(f"Error deleting article: {exc}")
        return ORJSONResponse(status_code=exc.status_code, content=exc.message)
    except Exception as exc:
        LOGGER.error(f"Unexpected exception: {exc}")
        return ORJSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiException.server_internal_error(),
        )


@router.post(
    "/{article_id}/like", response_model=Dict[str, Any], status_code=HTTP_201_CREATED
)
async def like_article(
    article_id: str,
    wiki_services: WikiManagerServices = Depends(WIKI_MANAGER_FACTORY),
    auth_user: AuthenticatedUser = Depends(AUTHENTICATION_PROVIDER),
):
    try:
        reaction = await wiki_services.article_service.like_article(
            article_id, auth_user
        )
        return ORJSONResponse(
            status_code=HTTP_201_CREATED,
            content=(
                reaction.model_dump() if hasattr(reaction, "model_dump") else reaction
            ),
        )
    except ApiException as exc:
        LOGGER.error(f"Error liking article: {exc}")
        return ORJSONResponse(status_code=exc.status_code, content=exc.message)
    except Exception as exc:
        LOGGER.error(f"Unexpected exception: {exc}")
        return ORJSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiException.server_internal_error(),
        )


@router.post(
    "/{article_id}/dislike",
    response_model=Dict[str, Any],
    status_code=HTTP_201_CREATED,
)
async def dislike_article(
    article_id: str,
    wiki_services: WikiManagerServices = Depends(WIKI_MANAGER_FACTORY),
    auth_user: AuthenticatedUser = Depends(AUTHENTICATION_PROVIDER),
):
    try:
        reaction = await wiki_services.article_service.dislike_article(
            article_id, auth_user
        )
        return ORJSONResponse(
            status_code=HTTP_201_CREATED,
            content=(
                reaction.model_dump() if hasattr(reaction, "model_dump") else reaction
            ),
        )
    except ApiException as exc:
        LOGGER.error(f"Error disliking article: {exc}")
        return ORJSONResponse(status_code=exc.status_code, content=exc.message)
    except Exception as exc:
        LOGGER.error(f"Unexpected exception: {exc}")
        return ORJSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiException.server_internal_error(),
        )


@router.delete("/{article_id}/cancel-reaction", status_code=HTTP_204_NO_CONTENT)
async def cancel_reaction(
    article_id: str,
    wiki_services: WikiManagerServices = Depends(WIKI_MANAGER_FACTORY),
    auth_user: AuthenticatedUser = Depends(AUTHENTICATION_PROVIDER),
):
    try:
        await wiki_services.article_service.cancel_reaction(article_id, auth_user)
        return Response(status_code=HTTP_204_NO_CONTENT)
    except ApiException as exc:
        LOGGER.error(f"Error canceling reaction: {exc}")
        return ORJSONResponse(status_code=exc.status_code, content=exc.message)
    except Exception as exc:
        LOGGER.error(f"Unexpected exception: {exc}")
        return ORJSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiException.server_internal_error(),
        )


@router.get("/{article_id}/reactions/list", response_model=Dict[str, Any])
async def load_reactions(
    article_id: str,
    page_size: int = 1,
    max_results: int = 20,
    direction: str = "DESC",
    wiki_services: WikiManagerServices = Depends(WIKI_MANAGER_FACTORY),
    auth_user: AuthenticatedUser = Depends(AUTHENTICATION_PROVIDER),
):
    try:
        reactions_data = await wiki_services.article_service.load_reactions(
            article_id=article_id,
            page_size=page_size,
            max_result=max_results,
            direction=direction,
        )
        return ORJSONResponse(
            status_code=HTTP_200_OK,
            content=reactions_data,
        )
    except ApiException as exc:
        LOGGER.error(f"Error getting reactions list: {exc}")
        return ORJSONResponse(status_code=exc.status_code, content=exc.message)
    except Exception as exc:
        LOGGER.error(f"Unexpected exception: {exc}")
        return ORJSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiException.server_internal_error(),
        )


@router.post(
    "/{article_id}/comment",
    response_model=Dict[str, Any],
    status_code=HTTP_201_CREATED,
)
async def add_comment(
    article_id: str,
    comment_request: AddCommentDTO,
    wiki_services: WikiManagerServices = Depends(WIKI_MANAGER_FACTORY),
    auth_user: AuthenticatedUser = Depends(AUTHENTICATION_PROVIDER),
):
    try:
        comment = await wiki_services.article_service.add_comment(
            article_id, comment_request.model_dump(), auth_user
        )
        return ORJSONResponse(
            status_code=HTTP_201_CREATED,
            content=(
                comment.model_dump() if hasattr(comment, "model_dump") else comment
            ),
        )
    except ApiException as exc:
        LOGGER.error(f"Error adding comment: {exc}")
        return ORJSONResponse(status_code=exc.status_code, content=exc.message)
    except Exception as exc:
        LOGGER.error(f"Unexpected exception: {exc}")
        return ORJSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiException.server_internal_error(),
        )


@router.get("/{article_id}/comments", response_model=Dict[str, Any])
async def load_comments(
    article_id: str,
    page_size: int = 1,
    max_results: int = 20,
    direction: str = "DESC",
    wiki_services: WikiManagerServices = Depends(WIKI_MANAGER_FACTORY),
    auth_user: AuthenticatedUser = Depends(AUTHENTICATION_PROVIDER),
):
    try:
        comments_data = await wiki_services.article_service.load_comments(
            article_id=article_id,
            page_size=page_size,
            max_result=max_results,
            direction=direction,
        )
        return ORJSONResponse(
            status_code=HTTP_200_OK,
            content=comments_data,
        )
    except ApiException as exc:
        LOGGER.error(f"Error getting comments list: {exc}")
        return ORJSONResponse(status_code=exc.status_code, content=exc.message)
    except Exception as exc:
        LOGGER.error(f"Unexpected exception: {exc}")
        return ORJSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiException.server_internal_error(),
        )


@router.delete("/comment/{comment_id}", status_code=HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: str,
    wiki_services: WikiManagerServices = Depends(WIKI_MANAGER_FACTORY),
    auth_user: AuthenticatedUser = Depends(AUTHENTICATION_PROVIDER),
):
    try:
        await wiki_services.article_service.delete_comment(comment_id, auth_user)
        return Response(status_code=HTTP_204_NO_CONTENT)
    except ApiException as exc:
        LOGGER.error(f"Error deleting comment: {exc}")
        return ORJSONResponse(status_code=exc.status_code, content=exc.message)
    except Exception as exc:
        LOGGER.error(f"Unexpected exception: {exc}")
        return ORJSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiException.server_internal_error(),
        )
