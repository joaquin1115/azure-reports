from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.auth.dependencies import require_admin, require_especialista
from app.models.models import Cliente, Tenant
from app.schemas.schemas import ClienteCreate, ClienteUpdate, ClienteOut, RecursoAzure, TenantCreate
from app.integrations.azure_rm import listar_subscriptions_por_tenant, obtener_recursos_por_tenant

router = APIRouter(prefix="/clientes", tags=["Clientes"])


def _validar_tenants_unicos(tenants: list[TenantCreate]) -> None:
    tenant_ids = [tenant.tenant_id_azure for tenant in tenants]
    if len(tenant_ids) != len(set(tenant_ids)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No se puede asociar el mismo tenant de Azure más de una vez al cliente.")


async def _obtener_cliente_con_tenants(db: AsyncSession, cliente_id: int) -> Cliente:
    result = await db.execute(select(Cliente).options(selectinload(Cliente.tenants)).where(Cliente.cliente_id == cliente_id))
    return result.scalar_one()


async def _commit_cliente(db: AsyncSession, cliente_id: int) -> Cliente:
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No se pudo guardar el cliente porque uno de sus tenants de Azure ya está duplicado.") from exc
    return await _obtener_cliente_con_tenants(db, cliente_id)


@router.get("", response_model=list[ClienteOut])
async def listar_clientes(db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin())):
    result = await db.execute(select(Cliente).options(selectinload(Cliente.tenants)).order_by(Cliente.nombre))
    return result.scalars().all()


@router.post("", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
async def crear_cliente(
    body: ClienteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin())
    ):
    _validar_tenants_unicos(body.tenants)
    cliente = Cliente(nombre=body.nombre)
    db.add(cliente)
    await db.flush()
    for t in body.tenants:
        db.add(Tenant(
            cliente_id=cliente.cliente_id,
            tenant_id_azure=t.tenant_id_azure,
            nombre=t.nombre))
    return await _commit_cliente(db, cliente.cliente_id)


@router.put("/{cliente_id}", response_model=ClienteOut)
async def actualizar_cliente(cliente_id: int, body: ClienteUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin())):
    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    if body.nombre is not None:
        cliente.nombre = body.nombre
    if body.activo is not None:
        cliente.activo = body.activo
    if body.tenants is not None:
        _validar_tenants_unicos(body.tenants)
        await db.execute(delete(Tenant).where(Tenant.cliente_id == cliente_id))
        for t in body.tenants:
            db.add(Tenant(cliente_id=cliente_id, tenant_id_azure=t.tenant_id_azure, nombre=t.nombre))
    return await _commit_cliente(db, cliente_id)


@router.patch("/{cliente_id}/desactivar", response_model=ClienteOut)
async def desactivar_cliente(cliente_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin())):
    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    cliente.activo = False
    return await _commit_cliente(db, cliente_id)


@router.get("/{cliente_id}/recursos", response_model=list[RecursoAzure])
async def obtener_recursos(cliente_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_especialista())):
    result = await db.execute(select(Tenant).where(Tenant.cliente_id == cliente_id))
    tenants = result.scalars().all()
    if not tenants:
        raise HTTPException(status_code=404, detail="El cliente no tiene tenants configurados")
    todos_recursos: list[RecursoAzure] = []
    for tenant in tenants:
        subscription_ids = await listar_subscriptions_por_tenant(tenant.tenant_id_azure)
        for subscription_id in subscription_ids:
            todos_recursos.extend(await obtener_recursos_por_tenant(tenant_id=tenant.tenant_id_azure, subscription_id=subscription_id))
    return todos_recursos
