from app.configs.environment import ENVIRONMENT_CONFIG
from app.services.article.article_service import ArticleService
from app.services.category.category_service import CategoryService
from app.services.health.health_check_service import HealthCheckService
from app.services.user.user_service import UserService
from app.storage.rds.clients.database_manager import DATA_BASE_MANAGER
from app.storage.rds.clients.keycloak_client import KeycloakClient
from app.storage.rds.datastore.article.article_store import ArticleStore
from app.storage.rds.datastore.category.category_store import CategoryStore
from app.storage.rds.datastore.health.health_check_provider import HealthCheckProvider
from app.storage.rds.datastore.media.media_store import MediaStore
from app.storage.rds.datastore.user.user_store import KeycloakDatastore


class WikiManagerServices:
    def __init__(
        self,
        health_check_service: HealthCheckService,
        category_service: CategoryService,
        article_service: ArticleService,
        user_service: UserService,
    ):
        self._health_check_service = health_check_service
        self._category_service = category_service
        self._article_service = article_service
        self._user_service = user_service

    @property
    def health_check_service(self) -> HealthCheckService:
        return self._health_check_service

    @property
    def category_service(self) -> CategoryService:
        return self._category_service

    @property
    def article_service(self) -> ArticleService:
        return self._article_service

    @property
    def user_service(self) -> UserService:
        return self._user_service


class ServicesFactory:
    def __init__(self, provider: WikiManagerServices):
        self._provider = provider

    def __call__(self) -> WikiManagerServices:
        return self._provider


HEALTH_CHECK_PROVIDER = HealthCheckProvider(DATA_BASE_MANAGER)
CATEGORY_STORE = CategoryStore(DATA_BASE_MANAGER)
ARTICLE_STORE = ArticleStore(DATA_BASE_MANAGER)
MEDIA_STORE = MediaStore(DATA_BASE_MANAGER)
KEYCLOAK_CLIENT = KeycloakClient(ENVIRONMENT_CONFIG)
USER_STORE = KeycloakDatastore(KEYCLOAK_CLIENT)

HEALTH_CHECK_SERVICE = HealthCheckService(HEALTH_CHECK_PROVIDER)
CATEGORY_SERVICE = CategoryService(CATEGORY_STORE)
ARTICLE_SERVICE = ArticleService(ARTICLE_STORE, CATEGORY_STORE, MEDIA_STORE)
USER_SERVICE = UserService(USER_STORE)

WIKI_MANAGER_SERVICES = WikiManagerServices(
    health_check_service=HEALTH_CHECK_SERVICE,
    category_service=CATEGORY_SERVICE,
    article_service=ARTICLE_SERVICE,
    user_service=USER_SERVICE,
)

WIKI_MANAGER_FACTORY = ServicesFactory(WIKI_MANAGER_SERVICES)
