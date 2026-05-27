import asyncio
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Reporte, Configuracion, RecursoConfig, Cliente, Tenant, Usuario, EstadoReporteEnum
from app.integrations import azure_rm, azure_advisor, blob_storage
from app.services.analisis_service import analizar_metrica
from app.services.word_service import generar_word

# In-memory SSE subscribers: reporte_id -> asyncio.Queue
_sse_subscribers: dict[str, asyncio.Queue] = {}


def suscribir_sse(reporte_id: str) -> asyncio.Queue:
    q = asyncio.Queue()
    _sse_subscribers[reporte_id] = q
    return q


def _notificar_sse(reporte_id: str, evento: dict):
    q = _sse_subscribers.get(str(reporte_id))
    if q:
        q.put_nowait(evento)


async def iniciar_generacion(
    db: AsyncSession,
    configuracion_id: uuid.UUID,
    usuario_id: uuid.UUID,
) -> Reporte:
    """Creates a Reporte record and launches async generation."""
    config = await db.get(Configuracion, configuracion_id)
    if not config:
        raise ValueError("Configuración no encontrada")

    reporte = Reporte(
        configuracion_id=configuracion_id,
        usuario_id=usuario_id,
        periodo_mes=config.periodo_mes,
        periodo_anio=config.periodo_anio,
        estado=EstadoReporteEnum.pendiente,
    )
    db.add(reporte)
    await db.flush()
    await db.refresh(reporte)

    # Launch background task
    asyncio.create_task(_ejecutar_generacion(reporte.id, configuracion_id, usuario_id))
    return reporte


async def _ejecutar_generacion(
    reporte_id: uuid.UUID,
    configuracion_id: uuid.UUID,
    usuario_id: uuid.UUID,
):
    """Background task: fetches data, generates Word, updates Reporte record."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        reporte = await db.get(Reporte, reporte_id)
        reporte.estado = EstadoReporteEnum.procesando
        reporte.inicio_generacion = datetime.utcnow()
        await db.commit()

        try:
            config = await db.get(Configuracion, configuracion_id)
            cliente = await db.get(Cliente, config.cliente_id)
            usuario = await db.get(Usuario, usuario_id)

            # Load tenants and resources
            tenants_result = await db.execute(
                select(Tenant).where(Tenant.cliente_id == cliente.id)
            )
            tenants = tenants_result.scalars().all()


            recursos_result = await db.execute(
                select(RecursoConfig).where(RecursoConfig.configuracion_id == configuracion_id)
            )
            recursos = recursos_result.scalars().all()

            # Use first tenant credentials (simplified; in prod each tenant has its own creds)
            tenant = tenants[0] if tenants else None
            if not tenant:
                raise ValueError("El cliente no tiene tenants configurados")
            
            subscription_ids = await azure_rm.listar_subscriptions_por_tenant(tenant.tenant_id_azure)

            # --- Recomendaciones (tenant consolidado) ---
            recomendaciones = []
            for subscription_id in subscription_ids:
                recomendaciones_sub = await azure_advisor.obtener_recomendaciones(
                    subscription_id=subscription_id,
                    gravedad=config.gravedad,
                )
                recomendaciones.extend(recomendaciones_sub)

            # --- Métricas por recurso ---
            _notificar_sse(str(reporte_id), {
                "evento": "progreso",
                "reporte_id": str(reporte_id),
                "etapa": "analisis_metricas",
                "estado_etapa": "iniciada",
                "mensaje": "Análisis de métricas en progreso",
            })

            resultados_por_recurso = []
            for recurso in recursos:
                metricas_raw = await azure_rm.obtener_metricas_recurso(
                    resource_id=recurso.resource_id_azure,
                    tipo=recurso.tipo,
                    periodo_mes=config.periodo_mes,
                    periodo_anio=config.periodo_anio,
                )
                print("metricas raw:", recurso.nombre, metricas_raw)
                metricas_analizadas = [
                    analizar_metrica(
                        nombre=nombre,
                        valores=datos["values"],
                        fechas=datos["dates"],
                    )
                    for nombre, datos in metricas_raw.items()
                ]
                resultados_por_recurso.append({
                    "nombre": recurso.nombre,
                    "tipo": recurso.tipo,
                    "metricas": metricas_analizadas,
                })

            _notificar_sse(str(reporte_id), {
                "evento": "progreso",
                "reporte_id": str(reporte_id),
                "etapa": "analisis_metricas",
                "estado_etapa": "completada",
                "mensaje": "Análisis de métricas completado",
            })

            # --- Word ---
            _notificar_sse(str(reporte_id), {
                "evento": "progreso",
                "reporte_id": str(reporte_id),
                "etapa": "redaccion_recomendaciones",
                "estado_etapa": "iniciada",
                "mensaje": "Redacción de recomendaciones en progreso",
            })

            word_bytes = generar_word(
                cliente_nombre=cliente.nombre,
                periodo_mes=config.periodo_mes,
                periodo_anio=config.periodo_anio,
                usuario_nombre=usuario.nombre,
                recomendaciones=recomendaciones,
                resultados_por_recurso=resultados_por_recurso,
            )

            _notificar_sse(str(reporte_id), {
                "evento": "progreso",
                "reporte_id": str(reporte_id),
                "etapa": "redaccion_recomendaciones",
                "estado_etapa": "completada",
                "mensaje": "Redacción de recomendaciones completada",
            })

            # --- Upload to Blob ---
            nombre_blob = f"{cliente.nombre}/{config.periodo_anio}-{config.periodo_mes:02d}/{reporte_id}.docx"
            await blob_storage.subir_documento(word_bytes, nombre_blob, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

            # --- Update reporte ---
            fin = datetime.utcnow()
            reporte.fin_generacion = fin
            reporte.tiempo_generacion_seg = (fin - reporte.inicio_generacion).total_seconds()
            reporte.url_pdf = nombre_blob
            reporte.estado = EstadoReporteEnum.completado
            await db.commit()

            _notificar_sse(str(reporte_id), {
                "evento": "completado",
                "reporte_id": str(reporte_id),
                "tiempo_seg": reporte.tiempo_generacion_seg,
            })

        except Exception as exc:
            reporte.estado = EstadoReporteEnum.error
            reporte.error_mensaje = str(exc)
            await db.commit()
            _notificar_sse(str(reporte_id), {
                "evento": "error",
                "reporte_id": str(reporte_id),
                "mensaje": str(exc),
            })
            raise
