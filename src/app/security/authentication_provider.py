from typing import List

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer

from app.configs.environment import ENVIRONMENT_CONFIG
from app.models.security.auth_user import AuthenticatedUser
from app.security.api_roles import ApiRoles
from app.security.auth_token_client import AuthTokenClient
from app.security.managers.authentication_manager import AuthenticationManager
from app.security.managers.jwt_authentication_manager import JWTAuthenticationManager
from app.security.managers.oauth2_authentication_manager import (
    OAuth2AuthenticationManager,
)


class AuthenticationProvider(HTTPBearer):
    def __init__(self, managers: List[AuthenticationManager], auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.managers = managers

    async def __call__(self, request: Request) -> AuthenticatedUser:
        credentials = await super().__call__(request)

        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )

        if credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme. Bearer token required.",
            )

        token = credentials.credentials

        for manager in self.managers:
            if manager.supports(token):
                return await manager.authenticate(token)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No suitable authentication manager found for this token.",
        )


class AuthenticationProviderMock:
    def __init__(self): ...

    def __call__(self) -> AuthenticatedUser:
        return AuthenticatedUser(
            **{
                "user_id": "9aaf7d8f-5492-41d9-97e9-cf5652ebe762",
                "username": "digijob",
                "email": "developer@wearedigijob.com",
                "scopes": "scopes",
                "roles": [ApiRoles.MANAGER, ApiRoles.EMPLOYEE, ApiRoles.DIRECTOR],
                "groups": ["group1", "group2"],
            }
        )


AUTH_TOKEN_CLIENT = AuthTokenClient(ENVIRONMENT_CONFIG)
JWT_AUTHENTICATION_MANAGER = JWTAuthenticationManager(
    AUTH_TOKEN_CLIENT, ENVIRONMENT_CONFIG
)

OAUTH_AUTHENTICATION_MANAGER = OAuth2AuthenticationManager(AUTH_TOKEN_CLIENT)
# AUTHENTICATION_PROVIDER = AuthenticationProvider([JWT_AUTHENTICATION_MANAGER])

AUTHENTICATION_PROVIDER = AuthenticationProviderMock()
