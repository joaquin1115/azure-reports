from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.catalog import get_recurrencia_id, get_tipo_recomendacion_id
from app.db.session import get_db
from app.auth.dependencies import require_especialista
from app.models.models import Cliente, Disparador, Recurso, Recurrencia, Usuario
from app.schemas.schemas import ClienteSimple, ProgramacionCreate, ProgramacionOut, RecursoDisparadorOut

router = APIRouter(prefix="/programaciones", tags=["Programaciones"])

_TIPO_RECOMENDACION_DB = {"alta": "Alta", "media": "Media", "ambas": "Baja"}
_TIPO_RECOMENDACION_LABEL = {"Alta": "Alta", "Media": "Alta y media", "Baja": "Alta, media y baja"}


def _recurso_out(recurso: Recurso) -> RecursoDisparadorOut:
    return RecursoDisparadorOut(id=recurso.recurso_id, azure_resource_id=recurso.azure_resource_id, nombre=recurso.azure_resource_id.split("/")[-1])


def _programacion_out(disparador: Disparador) -> ProgramacionOut:
    return ProgramacionOut.model_validate({
        "id": disparador.disparador_id,
        "cliente": ClienteSimple.model_validate(disparador.cliente),
        "tipo_recomendacion": _TIPO_RECOMENDACION_LABEL[disparador.tipo_recomendacion.nombre],
        "frecuencia": disparador.recurrencia.nombre,
        "proxima_ejecucion": disparador.proxima_ejecucion,
        "activa": disparador.activo,
        "creado_en": disparador.fecha_creacion,
        "recursos": [_recurso_out(r) for r in disparador.recursos],
    })


@router.get("", response_model=list[ProgramacionOut])
async def listar_programaciones(db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_especialista())):
    result = await db.execute(
        select(Disparador)
        .join(Disparador.recurrencia)
        .options(selectinload(Disparador.cliente), selectinload(Disparador.recursos), selectinload(Disparador.tipo_recomendacion), selectinload(Disparador.recurrencia))
        .where(Recurrencia.nombre == "Mensual")
        .order_by(Disparador.proxima_ejecucion)
    )
    return [_programacion_out(d) for d in result.scalars().all()]


@router.post("", response_model=ProgramacionOut, status_code=status.HTTP_201_CREATED)
async def crear_programacion(body: ProgramacionCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_especialista())):
    correo = current_user.get("email")
    usuario_result = await db.execute(select(Usuario).where(Usuario.correo == correo))
    usuario = usuario_result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not await db.get(Cliente, body.cliente_id):
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    disparador = Disparador(
        proxima_ejecucion=body.fecha_inicio,
        activo=True,
        usuario_id=usuario.usuario_id,
        cliente_id=body.cliente_id,
        tipo_recomendacion_id=await get_tipo_recomendacion_id(db, _TIPO_RECOMENDACION_DB[body.gravedad.value]),
        recurrencia_id=await get_recurrencia_id(db, "Mensual"),
    )
    db.add(disparador)
    await db.flush()
    for recurso in body.recursos:
        db.add(Recurso(azure_resource_id=recurso.resource_id_azure, disparador_id=disparador.disparador_id))
    await db.commit()

    result = await db.execute(
        select(Disparador)
        .options(selectinload(Disparador.cliente), selectinload(Disparador.recursos), selectinload(Disparador.tipo_recomendacion), selectinload(Disparador.recurrencia))
        .where(Disparador.disparador_id == disparador.disparador_id)
    )
    return _programacion_out(result.scalar_one())


@router.patch("/{disparador_id}/desactivar", response_model=ProgramacionOut)
async def desactivar_programacion(disparador_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_especialista())):
    result = await db.execute(
        select(Disparador)
        .options(selectinload(Disparador.cliente), selectinload(Disparador.recursos), selectinload(Disparador.tipo_recomendacion), selectinload(Disparador.recurrencia))
        .where(Disparador.disparador_id == disparador_id)
    )
    disparador = result.scalar_one_or_none()
    if not disparador:
        raise HTTPException(status_code=404, detail="Programación no encontrada")
    disparador.activo = False
    await db.commit()
    return _programacion_out(disparador)
