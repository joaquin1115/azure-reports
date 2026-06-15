import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.auth.dependencies import require_especialista
from app.models.models import Reporte, Disparador, Usuario, EstadoReporteEnum
from app.schemas.schemas import ReporteCreate, ReporteOut
from app.services import reporte_service
from app.integrations.blob_storage import generar_sas_url

router = APIRouter(prefix="/reportes", tags=["Reportes"])


def _reporte_out(reporte: Reporte) -> ReporteOut:
    tiempo = None
    if reporte.inicio_generacion and reporte.fin_generacion:
        tiempo = (reporte.fin_generacion - reporte.inicio_generacion).total_seconds()
    return ReporteOut.model_validate({
        "id": reporte.reporte_id,
        "disparador_id": reporte.disparador_id,
        "usuario_id": reporte.disparador.usuario_id,
        "periodo_mes": reporte.periodo_mes,
        "periodo_anio": reporte.periodo_anio,
        "inicio_generacion": reporte.inicio_generacion,
        "fin_generacion": reporte.fin_generacion,
        "tiempo_generacion_seg": tiempo,
        "url_docx": reporte.url_docx,
        "estado": reporte.estado_reporte.nombre,
        "creado_en": reporte.inicio_generacion,
    })


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def generar_reporte(body: ReporteCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_especialista())):
    correo = current_user.get("email")
    usuario_result = await db.execute(select(Usuario).where(Usuario.correo == correo))
    usuario = usuario_result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    try:
        reporte = await reporte_service.iniciar_generacion_manual(
            db=db,
            cliente_id=body.cliente_id,
            usuario_id=usuario.usuario_id,
            periodo_mes=body.periodo_mes,
            periodo_anio=body.periodo_anio,
            gravedad=body.gravedad,
            recursos=body.recursos,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"reporte_id": str(reporte.reporte_id), "estado": EstadoReporteEnum.pendiente.value}


@router.get("/sse/{reporte_id}")
async def sse_reporte(reporte_id: int, current_user: dict = Depends(require_especialista())):
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

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("", response_model=list[ReporteOut])
async def listar_reportes(cliente_id: int | None = None, periodo_mes: int | None = None, periodo_anio: int | None = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_especialista())):
    query = select(Reporte).join(Reporte.disparador).options(selectinload(Reporte.disparador), selectinload(Reporte.estado_reporte)).order_by(Reporte.inicio_generacion.desc().nullslast())
    if cliente_id:
        query = query.where(Disparador.cliente_id == cliente_id)
    if periodo_mes:
        query = query.where(Reporte.periodo_mes == periodo_mes)
    if periodo_anio:
        query = query.where(Reporte.periodo_anio == periodo_anio)
    result = await db.execute(query)
    return [_reporte_out(r) for r in result.scalars().all()]


@router.get("/{reporte_id}/descargar")
async def descargar_reporte(reporte_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_especialista())):
    reporte = await db.get(Reporte, reporte_id, options=[selectinload(Reporte.estado_reporte)])
    if not reporte:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    if reporte.estado_reporte.nombre != EstadoReporteEnum.completado.value:
        raise HTTPException(status_code=400, detail="El reporte aún no está disponible")
    url = await generar_sas_url(reporte.url_docx)
    return {"url_descarga": url}
