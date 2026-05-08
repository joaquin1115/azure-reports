import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.auth.dependencies import require_admin
from app.models.models import Usuario, AsignacionUsuarioCliente, RolEnum
from app.schemas.schemas import UsuarioCreate, UsuarioUpdate, UsuarioOut

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.get("", response_model=list[UsuarioOut])
async def listar_usuarios(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin()),
):
    result = await db.execute(
        select(Usuario)
        .options(selectinload(Usuario.asignaciones).selectinload(AsignacionUsuarioCliente.cliente))
        .order_by(Usuario.nombre)
    )
    usuarios = result.scalars().all()
    # Build response with clientes list
    out = []
    for u in usuarios:
        u_dict = {
            "id": u.id, "correo": u.correo, "nombre": u.nombre,
            "rol": u.rol, "activo": u.activo, "creado_en": u.creado_en,
            "clientes": [a.cliente for a in u.asignaciones],
        }
        out.append(UsuarioOut.model_validate(u_dict))
    return out


@router.post("", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    body: UsuarioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin()),
):
    existing = await db.execute(select(Usuario).where(Usuario.correo == body.correo))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese correo")

    usuario = Usuario(correo=body.correo, nombre=body.nombre, rol=body.rol)
    db.add(usuario)
    await db.flush()

    for cliente_id in body.cliente_ids:
        db.add(AsignacionUsuarioCliente(usuario_id=usuario.id, cliente_id=cliente_id))

    await db.commit()
    await db.refresh(usuario)
    return UsuarioOut.model_validate({
        "id": usuario.id, "correo": usuario.correo, "nombre": usuario.nombre,
        "rol": usuario.rol, "activo": usuario.activo, "creado_en": usuario.creado_en,
        "clientes": [],
    })


@router.put("/{usuario_id}", response_model=UsuarioOut)
async def actualizar_usuario(
    usuario_id: uuid.UUID,
    body: UsuarioUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin()),
):
    usuario = await db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if body.nombre is not None:
        usuario.nombre = body.nombre
    if body.rol is not None:
        usuario.rol = body.rol
    if body.activo is not None:
        usuario.activo = body.activo
    if body.cliente_ids is not None:
        await db.execute(
            delete(AsignacionUsuarioCliente).where(AsignacionUsuarioCliente.usuario_id == usuario_id)
        )
        for cliente_id in body.cliente_ids:
            db.add(AsignacionUsuarioCliente(usuario_id=usuario_id, cliente_id=cliente_id))

    await db.commit()
    await db.refresh(usuario)
    return UsuarioOut.model_validate({
        "id": usuario.id, "correo": usuario.correo, "nombre": usuario.nombre,
        "rol": usuario.rol, "activo": usuario.activo, "creado_en": usuario.creado_en,
        "clientes": [],
    })


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_usuario(
    usuario_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin()),
):
    usuario = await db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Prevent deleting last admin
    if usuario.rol == RolEnum.admin:
        admins = await db.execute(
            select(Usuario).where(Usuario.rol == RolEnum.admin, Usuario.activo == True)
        )
        if len(admins.scalars().all()) <= 1:
            raise HTTPException(
                status_code=409,
                detail="No se puede eliminar al único administrador activo del sistema",
            )

    await db.delete(usuario)
    await db.commit()
