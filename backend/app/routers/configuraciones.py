import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.auth.dependencies import require_especialista
from app.models.models import Configuracion, RecursoConfig, Programacion, Usuario
from app.schemas.schemas import (
    ConfiguracionCreate, ConfiguracionOut,
    ProgramacionCreate, ProgramacionOut,
)

router = APIRouter(tags=["Configuraciones y Programaciones"])


# ── Configuraciones ───────────────────────────────────────────────────────────
@router.get("/configuraciones", response_model=list[ConfiguracionOut])
async def listar_configuraciones(
    cliente_id: uuid.UUID | None = None,
    solo_guardadas: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_especialista()),
):
    query = select(Configuracion).options(selectinload(Configuracion.recursos))
    if cliente_id:
        query = query.where(Configuracion.cliente_id == cliente_id)
    if solo_guardadas:
        query = query.where(Configuracion.guardada == True)
    result = await db.execute(query)
    return result.scalars().all()


@router.post(
    "/configuraciones",
    response_model=ConfiguracionOut,
    status_code=status.HTTP_201_CREATED
)
async def crear_configuracion(
    body: ConfiguracionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_especialista()),
):
    config = Configuracion(
        cliente_id=body.cliente_id,
        nombre=body.nombre,
        periodo_mes=body.periodo_mes,
        periodo_anio=body.periodo_anio,
        gravedad=body.gravedad,
        guardada=body.guardada,
    )

    db.add(config)

    await db.flush()

    for r in body.recursos:
        db.add(
            RecursoConfig(
                configuracion_id=config.id,
                resource_id_azure=r.resource_id_azure,
                nombre=r.nombre,
                tipo=r.tipo,
            )
        )

    await db.commit()

    result = await db.execute(
        select(Configuracion)
        .options(selectinload(Configuracion.recursos))
        .where(Configuracion.id == config.id)
    )

    return result.scalar_one()


@router.delete("/configuraciones/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_configuracion(
    config_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_especialista()),
):
    config = await db.get(Configuracion, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")
    await db.delete(config)
    await db.commit()


# ── Programaciones ────────────────────────────────────────────────────────────
@router.get("/programaciones", response_model=list[ProgramacionOut])
async def listar_programaciones(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_especialista()),
):
    result = await db.execute(select(Programacion).order_by(Programacion.proxima_ejecucion))
    return result.scalars().all()


@router.post("/programaciones", response_model=ProgramacionOut, status_code=status.HTTP_201_CREATED)
async def crear_programacion(
    body: ProgramacionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_especialista()),
):
    correo = current_user.get("preferred_username") or current_user.get("upn")
    usuario_result = await db.execute(select(Usuario).where(Usuario.correo == correo))
    usuario = usuario_result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    prog = Programacion(
        usuario_id=usuario.id,
        configuracion_id=body.configuracion_id,
        fecha_inicio=body.fecha_inicio,
        frecuencia=body.frecuencia,
        proxima_ejecucion=body.fecha_inicio,
        activa=True,
    )
    db.add(prog)
    await db.commit()
    await db.refresh(prog)
    return prog


@router.patch("/programaciones/{prog_id}/desactivar", response_model=ProgramacionOut)
async def desactivar_programacion(
    prog_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_especialista()),
):
    prog = await db.get(Programacion, prog_id)
    if not prog:
        raise HTTPException(status_code=404, detail="Programación no encontrada")
    prog.activa = False
    await db.commit()
    await db.refresh(prog)
    return prog
