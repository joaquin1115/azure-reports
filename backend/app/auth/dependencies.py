import httpx
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.db.session import get_db
from app.models.models import RolEnum, Usuario

settings = get_settings()
bearer_scheme = HTTPBearer()

_jwks_cache: dict = {}


def _get_valid_audiences() -> str:
    configured = settings.azure_client_id.strip()
    if configured.startswith("api://"):
        return configured
    return f"api://{configured}"


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    async with httpx.AsyncClient() as client:
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
            audience=_get_valid_audiences(),
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {str(e)}",
        )


def require_role(*roles: RolEnum):
    async def dependency(
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> dict:
        correo = (
            current_user.get("preferred_username")
            or current_user.get("upn")
            or current_user.get("email")
        )
        if not correo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No se encontró el correo del usuario en el token",
            )

        print(f"Correo: {correo}")

        usuario_result = await db.execute(
            select(Usuario).where(func.lower(Usuario.correo) == correo.lower())
        )
        usuario = usuario_result.scalar_one_or_none()
        if not usuario or not usuario.activo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario no autorizado o inactivo",
            )

        if usuario.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta acción",
            )

        current_user["db_usuario_id"] = str(usuario.id)
        current_user["db_rol"] = usuario.rol
        return current_user
    return dependency


def require_admin():
    return require_role(RolEnum.admin)


def require_especialista():
    return require_role(RolEnum.especialista, RolEnum.admin)
