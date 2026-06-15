from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.catalog import get_recurrencia_id, get_tipo_recomendacion_id
from app.db.session import get_db
from app.auth.dependencies import require_especialista
from app.models.models import Disparador, Recurso, Recurrencia, Usuario
from app.schemas.schemas import ConfiguracionCreate, ConfiguracionOut, ProgramacionCreate, ProgramacionOut

router = APIRouter(tags=["Configuraciones y Programaciones"])


def _config_out(disparador: Disparador) -> ConfiguracionOut:
    return ConfiguracionOut.model_validate({
        "id": disparador.disparador_id,
        "cliente_id": disparador.cliente_id,
        "nombre": f"Disparador {disparador.disparador_id}",
        "periodo_mes": datetime.utcnow().month,
        "periodo_anio": datetime.utcnow().year,
        "gravedad": {"Alta": "alta", "Media": "media", "Baja": "ambas"}[disparador.tipo_recomendacion.nombre],
        "guardada": disparador.recurrencia.nombre == "Mensual",
        "creado_en": disparador.fecha_creacion,
        "recursos": [{"id": r.recurso_id, "resource_id_azure": r.azure_resource_id, "nombre": r.azure_resource_id.split("/")[-1], "tipo": "VM"} for r in disparador.recursos],
    })


def _programacion_out(disparador: Disparador) -> ProgramacionOut:
    return ProgramacionOut.model_validate({
        "id": disparador.disparador_id,
        "disparador_id": disparador.disparador_id,
        "fecha_inicio": disparador.fecha_creacion,
        "frecuencia": disparador.recurrencia.nombre,
        "proxima_ejecucion": disparador.proxima_ejecucion or disparador.fecha_creacion,
        "activa": disparador.activo,
        "creado_en": disparador.fecha_creacion,
    })


@router.get("/configuraciones", response_model=list[ConfiguracionOut])
async def listar_configuraciones(cliente_id: int | None = None, solo_guardadas: bool = False, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_especialista())):
    query = select(Disparador).options(selectinload(Disparador.recursos), selectinload(Disparador.tipo_recomendacion), selectinload(Disparador.recurrencia))
    if cliente_id:
        query = query.where(Disparador.cliente_id == cliente_id)
    if solo_guardadas:
        query = query.join(Disparador.recurrencia).where(Recurrencia.nombre == "Mensual")
    result = await db.execute(query)
    return [_config_out(d) for d in result.scalars().all()]


@router.post("/configuraciones", response_model=ConfiguracionOut, status_code=status.HTTP_201_CREATED)
async def crear_configuracion(body: ConfiguracionCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_especialista())):
    correo = current_user.get("email")
    usuario_result = await db.execute(select(Usuario).where(Usuario.correo == correo))
    usuario = usuario_result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    disparador = Disparador(
        proxima_ejecucion=None,
        activo=body.guardada,
        usuario_id=usuario.usuario_id,
        cliente_id=body.cliente_id,
        tipo_recomendacion_id=await get_tipo_recomendacion_id(db, {"alta": "Alta", "media": "Media", "ambas": "Baja"}[body.gravedad.value]),
        recurrencia_id=await get_recurrencia_id(db, "Mensual" if body.guardada else "Única"),
    )
    db.add(disparador)
    await db.flush()
    for recurso in body.recursos:
        db.add(Recurso(azure_resource_id=recurso.resource_id_azure, disparador_id=disparador.disparador_id))
    await db.commit()
    result = await db.execute(select(Disparador).options(selectinload(Disparador.recursos), selectinload(Disparador.tipo_recomendacion), selectinload(Disparador.recurrencia)).where(Disparador.disparador_id == disparador.disparador_id))
    return _config_out(result.scalar_one())


@router.delete("/configuraciones/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_configuracion(config_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_especialista())):
    disparador = await db.get(Disparador, config_id)
    if not disparador:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")
    await db.delete(disparador)
    await db.commit()


@router.get("/programaciones", response_model=list[ProgramacionOut])
async def listar_programaciones(db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_especialista())):
    result = await db.execute(select(Disparador).options(selectinload(Disparador.recurrencia)).where(Disparador.activo == True).order_by(Disparador.proxima_ejecucion))
    return [_programacion_out(d) for d in result.scalars().all()]


@router.post("/programaciones", response_model=ProgramacionOut, status_code=status.HTTP_201_CREATED)
async def crear_programacion(body: ProgramacionCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_especialista())):
    disparador_id = body.disparador_id or body.configuracion_id
    if disparador_id is None:
        raise HTTPException(status_code=422, detail="Debe indicar disparador_id")
    disparador = await db.get(Disparador, disparador_id, options=[selectinload(Disparador.recurrencia)])
    if not disparador:
        raise HTTPException(status_code=404, detail="Disparador no encontrado")
    disparador.proxima_ejecucion = body.fecha_inicio
    disparador.activo = True
    disparador.recurrencia_id = await get_recurrencia_id(db, body.frecuencia)
    await db.commit()
    await db.refresh(disparador, attribute_names=["recurrencia"])
    return _programacion_out(disparador)


@router.patch("/programaciones/{prog_id}/desactivar", response_model=ProgramacionOut)
async def desactivar_programacion(prog_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_especialista())):
    disparador = await db.get(Disparador, prog_id, options=[selectinload(Disparador.recurrencia)])
    if not disparador:
        raise HTTPException(status_code=404, detail="Programación no encontrada")
    disparador.activo = False
    await db.commit()
    return _programacion_out(disparador)
