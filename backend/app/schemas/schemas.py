from pydantic import BaseModel, EmailStr, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.models.models import RolEnum, GravedadEnum, TipoRecursoEnum, EstadoReporteEnum


# ── Usuario ───────────────────────────────────────────────────────────────────
class UsuarioCreate(BaseModel):
    correo: EmailStr
    nombre: str
    rol: RolEnum
    cliente_ids: list[UUID] = []


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    rol: Optional[RolEnum] = None
    cliente_ids: Optional[list[UUID]] = None
    activo: Optional[bool] = None


class UsuarioOut(BaseModel):
    id: UUID
    correo: str
    nombre: str
    rol: RolEnum
    activo: bool
    creado_en: datetime
    clientes: list["ClienteSimple"] = []

    model_config = {"from_attributes": True}


# ── Cliente ───────────────────────────────────────────────────────────────────
class TenantCreate(BaseModel):
    tenant_id_azure: str
    nombre: str


class TenantOut(BaseModel):
    id: UUID
    tenant_id_azure: str
    nombre: str

    model_config = {"from_attributes": True}


class ClienteCreate(BaseModel):
    nombre: str
    tenants: list[TenantCreate]


class ClienteUpdate(BaseModel):
    nombre: Optional[str] = None
    tenants: Optional[list[TenantCreate]] = None
    activo: Optional[bool] = None


class ClienteSimple(BaseModel):
    id: UUID
    nombre: str
    activo: bool

    model_config = {"from_attributes": True}


class ClienteOut(BaseModel):
    id: UUID
    nombre: str
    activo: bool
    creado_en: datetime
    tenants: list[TenantOut] = []

    model_config = {"from_attributes": True}


# ── Recurso Azure (no persistido, viene de Azure RM) ─────────────────────────
class RecursoAzure(BaseModel):
    resource_id: str
    nombre: str
    tipo: TipoRecursoEnum
    grupo_recursos: str
    tenant_id: str


# ── Configuracion ─────────────────────────────────────────────────────────────
class RecursoConfigCreate(BaseModel):
    resource_id_azure: str
    nombre: str
    tipo: TipoRecursoEnum


class ConfiguracionCreate(BaseModel):
    cliente_id: UUID
    nombre: str
    periodo_mes: int
    periodo_anio: int
    gravedad: GravedadEnum = GravedadEnum.ambas
    guardada: bool = False
    recursos: list[RecursoConfigCreate]

    @field_validator("periodo_mes")
    @classmethod
    def validar_mes(cls, v):
        if not 1 <= v <= 12:
            raise ValueError("El mes debe estar entre 1 y 12")
        return v


class RecursoConfigOut(BaseModel):
    id: UUID
    resource_id_azure: str
    nombre: str
    tipo: TipoRecursoEnum

    model_config = {"from_attributes": True}


class ConfiguracionOut(BaseModel):
    id: UUID
    cliente_id: UUID
    nombre: str
    periodo_mes: int
    periodo_anio: int
    gravedad: GravedadEnum
    guardada: bool
    creado_en: datetime
    recursos: list[RecursoConfigOut] = []

    model_config = {"from_attributes": True}


# ── Programacion ──────────────────────────────────────────────────────────────
class ProgramacionCreate(BaseModel):
    configuracion_id: UUID
    fecha_inicio: datetime
    frecuencia: str = "mensual"


class ProgramacionOut(BaseModel):
    id: UUID
    configuracion_id: UUID
    fecha_inicio: datetime
    frecuencia: str
    proxima_ejecucion: datetime
    activa: bool
    creado_en: datetime

    model_config = {"from_attributes": True}


# ── Reporte ───────────────────────────────────────────────────────────────────
class ReporteCreate(BaseModel):
    configuracion_id: UUID


class ReporteOut(BaseModel):
    id: UUID
    configuracion_id: UUID
    usuario_id: UUID
    periodo_mes: int
    periodo_anio: int
    inicio_generacion: Optional[datetime]
    fin_generacion: Optional[datetime]
    tiempo_generacion_seg: Optional[float]
    url_pdf: Optional[str]
    estado: EstadoReporteEnum
    creado_en: datetime

    model_config = {"from_attributes": True}


# Update forward refs
UsuarioOut.model_rebuild()
