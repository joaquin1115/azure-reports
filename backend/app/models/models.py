import uuid
from datetime import datetime
from sqlalchemy import (
    String, Boolean, DateTime, Float, ForeignKey,
    Enum as SAEnum, Integer, Text, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.session import Base
import enum


class RolEnum(str, enum.Enum):
    admin = "admin"
    especialista = "especialista"


class GravedadEnum(str, enum.Enum):
    alta = "alta"
    media = "media"
    ambas = "ambas"


class TipoRecursoEnum(str, enum.Enum):
    vm = "VM"
    db = "DB"
    asp = "ASP"


class EstadoReporteEnum(str, enum.Enum):
    pendiente = "pendiente"
    procesando = "procesando"
    completado = "completado"
    error = "error"


# ── Usuario ──────────────────────────────────────────────────────────────────
class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    correo: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[RolEnum] = mapped_column(SAEnum(RolEnum), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    asignaciones: Mapped[list["AsignacionUsuarioCliente"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    programaciones: Mapped[list["Programacion"]] = relationship(back_populates="usuario")
    reportes: Mapped[list["Reporte"]] = relationship(back_populates="usuario")


# ── Cliente ───────────────────────────────────────────────────────────────────
class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    tenants: Mapped[list["Tenant"]] = relationship(back_populates="cliente", cascade="all, delete-orphan")
    asignaciones: Mapped[list["AsignacionUsuarioCliente"]] = relationship(back_populates="cliente", cascade="all, delete-orphan")
    configuraciones: Mapped[list["Configuracion"]] = relationship(back_populates="cliente")
    reportes: Mapped[list["Reporte"]] = relationship(back_populates="cliente")


# ── Tenant ────────────────────────────────────────────────────────────────────
class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id", ondelete="CASCADE"))
    tenant_id_azure: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id_azure"),)

    cliente: Mapped["Cliente"] = relationship(back_populates="tenants")


# ── AsignacionUsuarioCliente ──────────────────────────────────────────────────
class AsignacionUsuarioCliente(Base):
    __tablename__ = "asignaciones_usuario_cliente"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id", ondelete="CASCADE"))
    asignado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("usuario_id", "cliente_id"),)

    usuario: Mapped["Usuario"] = relationship(back_populates="asignaciones")
    cliente: Mapped["Cliente"] = relationship(back_populates="asignaciones")


# ── Configuracion ─────────────────────────────────────────────────────────────
class Configuracion(Base):
    __tablename__ = "configuraciones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id", ondelete="CASCADE"))
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    periodo_mes: Mapped[int] = mapped_column(Integer, nullable=False)
    periodo_anio: Mapped[int] = mapped_column(Integer, nullable=False)
    gravedad: Mapped[GravedadEnum] = mapped_column(SAEnum(GravedadEnum), default=GravedadEnum.ambas)
    guardada: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cliente: Mapped["Cliente"] = relationship(back_populates="configuraciones")
    recursos: Mapped[list["RecursoConfig"]] = relationship(back_populates="configuracion", cascade="all, delete-orphan")
    programaciones: Mapped[list["Programacion"]] = relationship(back_populates="configuracion")
    reportes: Mapped[list["Reporte"]] = relationship(back_populates="configuracion")


# ── RecursoConfig ─────────────────────────────────────────────────────────────
class RecursoConfig(Base):
    __tablename__ = "recursos_config"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    configuracion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("configuraciones.id", ondelete="CASCADE"))
    resource_id_azure: Mapped[str] = mapped_column(Text, nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[TipoRecursoEnum] = mapped_column(SAEnum(TipoRecursoEnum), nullable=False)

    configuracion: Mapped["Configuracion"] = relationship(back_populates="recursos")


# ── Programacion ──────────────────────────────────────────────────────────────
class Programacion(Base):
    __tablename__ = "programaciones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    configuracion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("configuraciones.id", ondelete="CASCADE"))
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    frecuencia: Mapped[str] = mapped_column(String(50), nullable=False, default="mensual")
    proxima_ejecucion: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    usuario: Mapped["Usuario"] = relationship(back_populates="programaciones")
    configuracion: Mapped["Configuracion"] = relationship(back_populates="programaciones")


# ── Reporte ───────────────────────────────────────────────────────────────────
class Reporte(Base):
    __tablename__ = "reportes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id", ondelete="RESTRICT"))
    configuracion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("configuraciones.id", ondelete="RESTRICT"))
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"))
    periodo_mes: Mapped[int] = mapped_column(Integer, nullable=False)
    periodo_anio: Mapped[int] = mapped_column(Integer, nullable=False)
    inicio_generacion: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    fin_generacion: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    tiempo_generacion_seg: Mapped[float] = mapped_column(Float, nullable=True)
    url_pdf: Mapped[str] = mapped_column(Text, nullable=True)
    estado: Mapped[EstadoReporteEnum] = mapped_column(SAEnum(EstadoReporteEnum), default=EstadoReporteEnum.pendiente)
    error_mensaje: Mapped[str] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cliente: Mapped["Cliente"] = relationship(back_populates="reportes")
    configuracion: Mapped["Configuracion"] = relationship(back_populates="reportes")
    usuario: Mapped["Usuario"] = relationship(back_populates="reportes")
