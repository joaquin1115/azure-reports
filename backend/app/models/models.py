import enum
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


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
    pendiente = "Pendiente"
    procesando = "En proceso"
    completado = "Completado"
    error = "Error"


class Rol(Base):
    __tablename__ = "rol"

    rol_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500))

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="rol")


class TipoRecomendacion(Base):
    __tablename__ = "tipo_recomendacion"

    tipo_recomendacion_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500))

    disparadores: Mapped[list["Disparador"]] = relationship(back_populates="tipo_recomendacion")


class EstadoReporte(Base):
    __tablename__ = "estado_reporte"

    estado_reporte_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500))

    reportes: Mapped[list["Reporte"]] = relationship(back_populates="estado_reporte")


class Recurrencia(Base):
    __tablename__ = "recurrencia"

    recurrencia_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500))

    disparadores: Mapped[list["Disparador"]] = relationship(back_populates="recurrencia")


class Cliente(Base):
    __tablename__ = "cliente"

    cliente_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    tenants: Mapped[list["Tenant"]] = relationship(back_populates="cliente", cascade="all, delete-orphan")
    disparadores: Mapped[list["Disparador"]] = relationship(back_populates="cliente")

    @property
    def id(self) -> int:
        return self.cliente_id


class Tenant(Base):
    __tablename__ = "tenant"

    tenant_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id_azure: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("cliente.cliente_id"), nullable=False)

    cliente: Mapped[Cliente] = relationship(back_populates="tenants")

    @property
    def id(self) -> int:
        return self.tenant_id


class Usuario(Base):
    __tablename__ = "usuario"

    usuario_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    correo: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    rol_id: Mapped[int] = mapped_column(ForeignKey("rol.rol_id"), nullable=False)

    rol: Mapped[Rol] = relationship(back_populates="usuarios")
    disparadores: Mapped[list["Disparador"]] = relationship(back_populates="usuario")

    @property
    def id(self) -> int:
        return self.usuario_id

    @property
    def rol_nombre(self) -> str:
        return self.rol.nombre if self.rol else ""


class Disparador(Base):
    __tablename__ = "disparador"

    disparador_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    proxima_ejecucion: Mapped[datetime | None] = mapped_column(DateTime)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"), nullable=False)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("cliente.cliente_id"), nullable=False)
    tipo_recomendacion_id: Mapped[int] = mapped_column(ForeignKey("tipo_recomendacion.tipo_recomendacion_id"), nullable=False)
    recurrencia_id: Mapped[int] = mapped_column(ForeignKey("recurrencia.recurrencia_id"), nullable=False)

    usuario: Mapped[Usuario] = relationship(back_populates="disparadores")
    cliente: Mapped[Cliente] = relationship(back_populates="disparadores")
    tipo_recomendacion: Mapped[TipoRecomendacion] = relationship(back_populates="disparadores")
    recurrencia: Mapped[Recurrencia] = relationship(back_populates="disparadores")
    recursos: Mapped[list["Recurso"]] = relationship(back_populates="disparador", cascade="all, delete-orphan")
    reportes: Mapped[list["Reporte"]] = relationship(back_populates="disparador")

    @property
    def id(self) -> int:
        return self.disparador_id


class Recurso(Base):
    __tablename__ = "recurso"

    recurso_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    azure_resource_id: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    disparador_id: Mapped[int] = mapped_column(ForeignKey("disparador.disparador_id"), nullable=False)

    disparador: Mapped[Disparador] = relationship(back_populates="recursos")

    @property
    def id(self) -> int:
        return self.recurso_id


class Reporte(Base):
    __tablename__ = "reporte"
    __table_args__ = (CheckConstraint("periodo_mes BETWEEN 1 AND 12", name="chk_reporte_periodo_mes"),)

    reporte_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    periodo_mes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    periodo_anio: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    inicio_generacion: Mapped[datetime | None] = mapped_column(DateTime)
    fin_generacion: Mapped[datetime | None] = mapped_column(DateTime)
    url_docx: Mapped[str | None] = mapped_column(String(2048))
    error_mensaje: Mapped[str | None] = mapped_column(Text)
    estado_reporte_id: Mapped[int] = mapped_column(ForeignKey("estado_reporte.estado_reporte_id"), nullable=False)
    disparador_id: Mapped[int] = mapped_column(ForeignKey("disparador.disparador_id"), nullable=False)

    estado_reporte: Mapped[EstadoReporte] = relationship(back_populates="reportes")
    disparador: Mapped[Disparador] = relationship(back_populates="reportes")

    @property
    def id(self) -> int:
        return self.reporte_id

    @property
    def estado(self) -> str:
        return self.estado_reporte.nombre if self.estado_reporte else ""

    @property
    def url_pdf(self) -> str | None:
        return self.url_docx
