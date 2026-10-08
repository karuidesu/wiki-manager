from fastapi import APIRouter

from app.api.routes.article.article_api import router as article_router
from app.api.routes.category.category_api import router as category_router
from app.api.routes.health.health_check_api import router
from app.api.routes.user.user_api import router as user_router

api_router = APIRouter(prefix="/api/v1/wiki")

api_router.include_router(router, tags=["Health"])
api_router.include_router(category_router, prefix="/categories", tags=["Category"])
api_router.include_router(article_router, prefix="/articles", tags=["Article"])
api_router.include_router(user_router, prefix="/users", tags=["User"])
