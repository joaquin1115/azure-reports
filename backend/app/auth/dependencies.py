import httpx
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import get_settings
from app.models.models import RolEnum

settings = get_settings()
bearer_scheme = HTTPBearer()

_jwks_cache: dict = {}


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    async with httpx.AsyncClient() as client:
        console.log(f"Fetching JWKS from {settings.jwks_uri}")
        resp = await client.get(settings.jwks_uri)
        resp.raise_for_status()
        _jwks_cache = resp.json()
    return _jwks_cache


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    token = credentials.credentials
    try:
        jwks = await _get_jwks()
        header = jwt.get_unverified_header(token)
        key = next(
            (k for k in jwks["keys"] if k["kid"] == header["kid"]), None
        )
        if not key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Clave pública no encontrada")

        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.azure_client_id,
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {str(e)}",
        )


def require_role(*roles: RolEnum):
    async def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        # App roles come in the "roles" claim from Entra ID
        user_roles = current_user.get("roles", [])
        if not any(r.value in user_roles for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta acción",
            )
        return current_user
    return dependency


def require_admin():
    return require_role(RolEnum.admin)


def require_especialista():
    return require_role(RolEnum.especialista, RolEnum.admin)
