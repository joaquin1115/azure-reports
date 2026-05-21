import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.auth.dependencies import require_admin, require_especialista
from app.models.models import Cliente, Tenant, Reporte
from app.schemas.schemas import ClienteCreate, ClienteUpdate, ClienteOut, RecursoAzure
from app.integrations.azure_rm import (
    listar_subscriptions_por_tenant,
    obtener_recursos_por_tenant,
)

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get("", response_model=list[ClienteOut])
async def listar_clientes(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin()),
):
    result = await db.execute(
        select(Cliente).options(selectinload(Cliente.tenants)).order_by(Cliente.nombre)
    )
    return result.scalars().all()


@router.post("", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
async def crear_cliente(
    body: ClienteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin()),
):
    cliente = Cliente(nombre=body.nombre)
    db.add(cliente)
    await db.flush()

    for t in body.tenants:
        tenant = Tenant(
            cliente_id=cliente.id,
            tenant_id_azure=t.tenant_id_azure,
            nombre=t.nombre,
        )
        db.add(tenant)

    await db.commit()
    await db.refresh(cliente)
    return cliente


@router.put("/{cliente_id}", response_model=ClienteOut)
async def actualizar_cliente(
    cliente_id: uuid.UUID,
    body: ClienteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin()),
):
    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    if body.nombre is not None:
        cliente.nombre = body.nombre
    if body.activo is not None:
        cliente.activo = body.activo
    if body.tenants is not None:
        await db.execute(delete(Tenant).where(Tenant.cliente_id == cliente_id))
        for t in body.tenants:
            db.add(Tenant(cliente_id=cliente_id, tenant_id_azure=t.tenant_id_azure, nombre=t.nombre))

    await db.commit()
    await db.refresh(cliente)
    return cliente


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_cliente(
    cliente_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin()),
):
    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    reportes = await db.execute(select(Reporte).where(Reporte.cliente_id == cliente_id))
    if reportes.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar un cliente con reportes en el historial. Archívelo en su lugar.",
        )

    await db.delete(cliente)
    await db.commit()


@router.get("/{cliente_id}/recursos", response_model=list[RecursoAzure])
async def obtener_recursos(
    cliente_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_especialista()),
):
    """Returns all Azure resources available for a client's tenants."""
    result = await db.execute(select(Tenant).where(Tenant.cliente_id == cliente_id))
    tenants = result.scalars().all()
    if not tenants:
        raise HTTPException(status_code=404, detail="El cliente no tiene tenants configurados")

    todos_recursos: list[RecursoAzure] = []
    for tenant in tenants:
        subscription_ids = await listar_subscriptions_por_tenant(tenant.tenant_id_azure)
        for subscription_id in subscription_ids:
            recursos = await obtener_recursos_por_tenant(
                tenant_id=tenant.tenant_id_azure,
                subscription_id=subscription_id,
            )
            todos_recursos.extend(recursos)
    return todos_recursos
