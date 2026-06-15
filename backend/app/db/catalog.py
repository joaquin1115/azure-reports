from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import EstadoReporte, Recurrencia, Rol, TipoRecomendacion


async def get_catalog_id(db: AsyncSession, model: type, id_attr: str, nombre: str) -> int:
    result = await db.execute(select(model).where(model.nombre == nombre))
    row = result.scalar_one_or_none()
    if row is None:
        raise ValueError(f"No existe el valor de catálogo requerido: {model.__tablename__}.{nombre}")
    return getattr(row, id_attr)


async def get_estado_reporte_id(db: AsyncSession, nombre: str) -> int:
    return await get_catalog_id(db, EstadoReporte, "estado_reporte_id", nombre)


async def get_recurrencia_id(db: AsyncSession, nombre: str) -> int:
    return await get_catalog_id(db, Recurrencia, "recurrencia_id", nombre)


async def get_tipo_recomendacion_id(db: AsyncSession, nombre: str) -> int:
    return await get_catalog_id(db, TipoRecomendacion, "tipo_recomendacion_id", nombre)


async def get_rol_id(db: AsyncSession, nombre: str) -> int:
    return await get_catalog_id(db, Rol, "rol_id", nombre)
