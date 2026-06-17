import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.catalog import get_estado_reporte_id, get_recurrencia_id, get_tipo_recomendacion_id
from app.models.models import (
    Cliente,
    Disparador,
    EstadoReporteEnum,
    GravedadEnum,
    Recurso,
    Reporte,
    Tenant,
    TipoRecursoEnum,
    Usuario,
)
from app.integrations import azure_rm, azure_advisor, blob_storage
from app.services.analisis_service import analizar_metrica
from app.services.word_service import generar_word

_sse_subscribers: dict[str, asyncio.Queue] = {}


def suscribir_sse(reporte_id: str) -> asyncio.Queue:
    q = asyncio.Queue()
    _sse_subscribers[reporte_id] = q
    return q


def _notificar_sse(reporte_id: str, evento: dict):
    q = _sse_subscribers.get(str(reporte_id))
    if q:
        q.put_nowait(evento)

def obtener_tipo_recurso(resource_id: str) -> TipoRecursoEnum:
    resource_id = resource_id.lower()

    if "/providers/microsoft.compute/virtualmachines/" in resource_id:
        return TipoRecursoEnum.vm

    if "/providers/microsoft.sql/servers/" in resource_id and "/databases/" in resource_id:
        return TipoRecursoEnum.db

    if "/providers/microsoft.web/serverfarms/" in resource_id:
        return TipoRecursoEnum.asp

    raise ValueError(f"No se pudo determinar el tipo del recurso: {resource_id}")

async def iniciar_generacion_manual(
    db: AsyncSession,
    *,
    cliente_id: int,
    usuario_id: int,
    periodo_mes: int,
    periodo_anio: int,
    gravedad: GravedadEnum,
    recursos: list,
) -> Reporte:
    """Registra un disparador de recurrencia Única y crea el reporte asociado."""
    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise ValueError("Cliente no encontrado")

    disparador = Disparador(
        proxima_ejecucion=None,
        activo=False,
        usuario_id=usuario_id,
        cliente_id=cliente_id,
        tipo_recomendacion_id=await get_tipo_recomendacion_id(db, {"alta": "Alta", "media": "Media", "ambas": "Baja"}[gravedad.value]),
        recurrencia_id=await get_recurrencia_id(db, "Única"),
    )
    db.add(disparador)
    await db.flush()

    for recurso in recursos:
        db.add(Recurso(azure_resource_id=recurso.resource_id_azure, disparador_id=disparador.disparador_id))

    reporte = Reporte(
        disparador_id=disparador.disparador_id,
        periodo_mes=periodo_mes,
        periodo_anio=periodo_anio,
        estado_reporte_id=await get_estado_reporte_id(db, EstadoReporteEnum.pendiente.value),
    )
    db.add(reporte)
    await db.flush()
    await db.commit()
    await db.refresh(reporte)

    asyncio.create_task(_ejecutar_generacion(reporte.reporte_id, usuario_id))
    return reporte


async def iniciar_generacion_desde_disparador(
    db: AsyncSession,
    *,
    disparador_id: int,
    periodo_mes: int,
    periodo_anio: int,
) -> Reporte:
    disparador = await db.get(Disparador, disparador_id)
    if not disparador:
        raise ValueError("Disparador no encontrado")

    reporte = Reporte(
        disparador_id=disparador.disparador_id,
        periodo_mes=periodo_mes,
        periodo_anio=periodo_anio,
        estado_reporte_id=await get_estado_reporte_id(db, EstadoReporteEnum.pendiente.value),
    )
    db.add(reporte)
    await db.flush()
    await db.commit()
    await db.refresh(reporte)
    asyncio.create_task(_ejecutar_generacion(reporte.reporte_id, disparador.usuario_id))
    return reporte


async def _set_estado(db: AsyncSession, reporte: Reporte, estado: EstadoReporteEnum) -> None:
    reporte.estado_reporte_id = await get_estado_reporte_id(db, estado.value)


async def _ejecutar_generacion(reporte_id: int, usuario_id: int):
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        reporte = await db.get(Reporte, reporte_id, options=[selectinload(Reporte.disparador).selectinload(Disparador.recursos), selectinload(Reporte.disparador).selectinload(Disparador.tipo_recomendacion)])
        if not reporte:
            print(f"Reporte {reporte_id} no encontrado; se cancela la generación")
            return

        await _set_estado(db, reporte, EstadoReporteEnum.procesando)
        reporte.inicio_generacion = datetime.utcnow()
        await db.commit()

        try:
            _notificar_sse(str(reporte_id), {"evento": "progreso", "reporte_id": str(reporte_id), "etapa": "analisis_metricas", "estado_etapa": "iniciada", "mensaje": "Análisis de métricas en progreso"})

            disparador = reporte.disparador
            cliente = await db.get(Cliente, disparador.cliente_id)
            tenants_result = await db.execute(select(Tenant).where(Tenant.cliente_id == cliente.cliente_id))
            tenants = tenants_result.scalars().all()
            tenant = tenants[0] if tenants else None
            if not tenant:
                raise ValueError("El cliente no tiene tenants configurados")

            resultados_por_recurso = []

            for recurso in disparador.recursos:
                tipo_recurso = obtener_tipo_recurso(recurso.azure_resource_id)

                metricas_raw = await azure_rm.obtener_metricas_recurso(
                    resource_id=recurso.azure_resource_id,
                    tipo=tipo_recurso,
                    periodo_mes=reporte.periodo_mes,
                    periodo_anio=reporte.periodo_anio
                )

                metricas_analizadas = [
                    analizar_metrica(
                        nombre=nombre,
                        valores=datos["values"],
                        fechas=datos["dates"]
                    )
                    for nombre, datos in metricas_raw.items()
                ]

                resultados_por_recurso.append({
                    "nombre": recurso.azure_resource_id.split("/")[-1],
                    "tipo": tipo_recurso,
                    "metricas": metricas_analizadas
                })
            
            _notificar_sse(str(reporte_id), {"evento": "progreso", "reporte_id": str(reporte_id), "etapa": "analisis_metricas", "estado_etapa": "completada", "mensaje": "Análisis de métricas completado"})
            _notificar_sse(str(reporte_id), {"evento": "progreso", "reporte_id": str(reporte_id), "etapa": "redaccion_recomendaciones", "estado_etapa": "iniciada", "mensaje": "Redacción de recomendaciones en progreso"})

            gravedad = {"Alta": GravedadEnum.alta, "Media": GravedadEnum.media, "Baja": GravedadEnum.ambas}[disparador.tipo_recomendacion.nombre]
            recomendaciones = []
            subscription_ids = await azure_rm.listar_subscriptions_por_tenant(tenant.tenant_id_azure)
            for subscription_id in subscription_ids:
                recomendaciones.extend(await azure_advisor.obtener_recomendaciones(subscription_id=subscription_id, gravedad=gravedad, tenant_id=tenant.tenant_id_azure))

            _notificar_sse(str(reporte_id), {"evento": "progreso", "reporte_id": str(reporte_id), "etapa": "redaccion_recomendaciones", "estado_etapa": "completada", "mensaje": "Redacción de recomendaciones completada"})
            _notificar_sse(str(reporte_id), {"evento": "progreso", "reporte_id": str(reporte_id), "etapa": "preparacion_documento", "estado_etapa": "iniciada", "mensaje": "Preparación del documento en progreso"})

            usuario = await db.get(Usuario, usuario_id)
            word_bytes = generar_word(cliente_nombre=cliente.nombre, periodo_mes=reporte.periodo_mes, periodo_anio=reporte.periodo_anio, usuario_nombre=usuario.nombre, recomendaciones=recomendaciones, resultados_por_recurso=resultados_por_recurso)
            nombre_blob = f"{cliente.nombre}/{reporte.periodo_anio}-{reporte.periodo_mes:02d}/{reporte_id}.docx"
            await blob_storage.subir_documento(word_bytes, nombre_blob, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

            fin = datetime.utcnow()
            reporte.fin_generacion = fin
            reporte.url_docx = nombre_blob
            await _set_estado(db, reporte, EstadoReporteEnum.completado)
            await db.commit()
            _notificar_sse(str(reporte_id), {"evento": "completado", "reporte_id": str(reporte_id), "tiempo_seg": (fin - reporte.inicio_generacion).total_seconds()})
        except Exception as exc:
            await _set_estado(db, reporte, EstadoReporteEnum.error)
            reporte.error_mensaje = str(exc)
            await db.commit()
            _notificar_sse(str(reporte_id), {"evento": "error", "reporte_id": str(reporte_id), "mensaje": str(exc)})
            print(f"Error generando reporte {reporte_id}: {exc}")
