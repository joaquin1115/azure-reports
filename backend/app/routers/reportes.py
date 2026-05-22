import asyncio
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_especialista
from app.models.models import Reporte, Configuracion, AsignacionUsuarioCliente, Usuario, EstadoReporteEnum
from app.schemas.schemas import ReporteCreate, ReporteOut
from app.services import reporte_service
from app.integrations.blob_storage import generar_sas_url

router = APIRouter(prefix="/reportes", tags=["Reportes"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def generar_reporte(
    body: ReporteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_especialista()),
):
    """Initiates async report generation. Returns reporte_id immediately."""
    print(current_user)
    correo = current_user.get("email")
    print(correo)
    usuario_result = await db.execute(select(Usuario).where(Usuario.correo == correo))
    usuario = usuario_result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    reporte = await reporte_service.iniciar_generacion(
        db=db,
        configuracion_id=body.configuracion_id,
        usuario_id=usuario.id,
    )
    return {"reporte_id": str(reporte.id), "estado": reporte.estado}


@router.get("/sse/{reporte_id}")
async def sse_reporte(
    reporte_id: uuid.UUID,
    current_user: dict = Depends(require_especialista()),
):
    """SSE endpoint: streams progress events for a report generation."""
    queue = reporte_service.suscribir_sse(str(reporte_id))

    async def event_generator():
        try:
            while True:
                try:
                    evento = await asyncio.wait_for(queue.get(), timeout=60)
                    yield f"data: {json.dumps(evento)}\n\n"
                    if evento.get("evento") in ("completado", "error"):
                        break
                except asyncio.TimeoutError:
                    yield "data: {\"evento\": \"ping\"}\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("", response_model=list[ReporteOut])
async def listar_reportes(
    cliente_id: uuid.UUID | None = None,
    periodo_mes: int | None = None,
    periodo_anio: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_especialista()),
):
    """Returns reports visible to the current user (filtered by assigned clients)."""
    correo = current_user.get("preferred_username") or current_user.get("upn")
    usuario_result = await db.execute(select(Usuario).where(Usuario.correo == correo))
    usuario = usuario_result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Get assigned clients
    asig_result = await db.execute(
        select(AsignacionUsuarioCliente.cliente_id).where(
            AsignacionUsuarioCliente.usuario_id == usuario.id
        )
    )
    cliente_ids = [row[0] for row in asig_result.all()]

    query = (
        select(Reporte)
        .options(selectinload(Reporte.cliente))
        .where(Reporte.cliente_id.in_(cliente_ids))
        .order_by(Reporte.creado_en.desc())
    )
    if cliente_id:
        query = query.where(Reporte.cliente_id == cliente_id)
    if periodo_mes:
        query = query.where(Reporte.periodo_mes == periodo_mes)
    if periodo_anio:
        query = query.where(Reporte.periodo_anio == periodo_anio)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{reporte_id}/descargar")
async def descargar_reporte(
    reporte_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_especialista()),
):
    """Returns a time-limited SAS URL to download the PDF."""
    reporte = await db.get(Reporte, reporte_id)
    if not reporte:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    if reporte.estado != EstadoReporteEnum.completado:
        raise HTTPException(status_code=400, detail="El reporte aún no está disponible")

    url = await generar_sas_url(reporte.url_pdf)
    return {"url_descarga": url}
