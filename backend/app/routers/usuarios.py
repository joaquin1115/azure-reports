from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.catalog import get_rol_id
from app.db.session import get_db
from app.auth.dependencies import require_admin
from app.models.models import Rol, RolEnum, Usuario
from app.schemas.schemas import UsuarioCreate, UsuarioUpdate, UsuarioOut

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


def _usuario_out(usuario: Usuario) -> UsuarioOut:
    return UsuarioOut.model_validate({
        "id": usuario.usuario_id,
        "correo": usuario.correo,
        "nombre": usuario.nombre,
        "rol": {"Administrador": "admin", "Especialista": "especialista"}[usuario.rol.nombre],
        "activo": usuario.activo,
        "creado_en": usuario.creado_en,
        "clientes": [],
    })


@router.get("", response_model=list[UsuarioOut])
async def listar_usuarios(db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin())):
    result = await db.execute(select(Usuario).options(selectinload(Usuario.rol)).order_by(Usuario.nombre))
    return [_usuario_out(u) for u in result.scalars().all()]


@router.post("", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
async def crear_usuario(body: UsuarioCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin())):
    existing = await db.execute(select(Usuario).where(Usuario.correo == body.correo))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese correo")
    usuario = Usuario(correo=body.correo, nombre=body.nombre, rol_id=await get_rol_id(db, {"admin": "Administrador", "especialista": "Especialista"}[body.rol.value]))
    db.add(usuario)
    await db.commit()
    await db.refresh(usuario, attribute_names=["rol"])
    return _usuario_out(usuario)


@router.put("/{usuario_id}", response_model=UsuarioOut)
async def actualizar_usuario(usuario_id: int, body: UsuarioUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin())):
    usuario = await db.get(Usuario, usuario_id, options=[selectinload(Usuario.rol)])
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if body.nombre is not None:
        usuario.nombre = body.nombre
    if body.rol is not None:
        usuario.rol_id = await get_rol_id(db, {"admin": "Administrador", "especialista": "Especialista"}[body.rol.value])
    if body.activo is not None:
        usuario.activo = body.activo
    await db.commit()
    await db.refresh(usuario, attribute_names=["rol"])
    return _usuario_out(usuario)


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_usuario(usuario_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin())):
    usuario = await db.get(Usuario, usuario_id, options=[selectinload(Usuario.rol)])
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if usuario.rol.nombre == "Administrador":
        admins = await db.execute(select(Usuario).join(Usuario.rol).where(Rol.nombre == "Administrador", Usuario.activo == True))
        if len(admins.scalars().all()) <= 1:
            raise HTTPException(status_code=409, detail="No se puede eliminar al único administrador activo del sistema")
    await db.delete(usuario)
    await db.commit()
