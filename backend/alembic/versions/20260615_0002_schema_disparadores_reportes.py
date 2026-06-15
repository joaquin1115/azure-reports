"""replace persistence model with disparadores/reportes schema

Revision ID: 20260615_0002
Revises: 20260603_0001
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa

revision = "20260615_0002"
down_revision = "20260603_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in (
        "recursos_config",
        "reportes",
        "programaciones",
        "configuraciones",
        "asignaciones_usuario_cliente",
        "tenants",
        "usuarios",
        "clientes",
    ):
        op.execute(sa.text(f"DROP TABLE IF EXISTS {table} CASCADE"))

    op.create_table("rol", sa.Column("rol_id", sa.Integer(), sa.Identity(always=True), primary_key=True), sa.Column("nombre", sa.String(100), nullable=False), sa.Column("descripcion", sa.String(500)))
    op.create_table("tipo_recomendacion", sa.Column("tipo_recomendacion_id", sa.Integer(), sa.Identity(always=True), primary_key=True), sa.Column("nombre", sa.String(100), nullable=False), sa.Column("descripcion", sa.String(500)))
    op.create_table("estado_reporte", sa.Column("estado_reporte_id", sa.Integer(), sa.Identity(always=True), primary_key=True), sa.Column("nombre", sa.String(100), nullable=False), sa.Column("descripcion", sa.String(500)))
    op.create_table("recurrencia", sa.Column("recurrencia_id", sa.Integer(), sa.Identity(always=True), primary_key=True), sa.Column("nombre", sa.String(100), nullable=False), sa.Column("descripcion", sa.String(500)))
    op.create_table("cliente", sa.Column("cliente_id", sa.Integer(), sa.Identity(always=True), primary_key=True), sa.Column("nombre", sa.String(200), nullable=False), sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("creado_en", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    op.create_table("tenant", sa.Column("tenant_id", sa.Integer(), sa.Identity(always=True), primary_key=True), sa.Column("tenant_id_azure", sa.String(50), nullable=False), sa.Column("nombre", sa.String(200), nullable=False), sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("cliente.cliente_id"), nullable=False), sa.UniqueConstraint("tenant_id_azure", name="uq_tenant_tenant_id_azure"))
    op.create_table("usuario", sa.Column("usuario_id", sa.Integer(), sa.Identity(always=True), primary_key=True), sa.Column("correo", sa.String(320), nullable=False), sa.Column("nombre", sa.String(200), nullable=False), sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("creado_en", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")), sa.Column("rol_id", sa.Integer(), sa.ForeignKey("rol.rol_id"), nullable=False), sa.UniqueConstraint("correo", name="uq_usuario_correo"))
    op.create_table("disparador", sa.Column("disparador_id", sa.Integer(), sa.Identity(always=True), primary_key=True), sa.Column("fecha_creacion", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")), sa.Column("proxima_ejecucion", sa.DateTime()), sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuario.usuario_id"), nullable=False), sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("cliente.cliente_id"), nullable=False), sa.Column("tipo_recomendacion_id", sa.Integer(), sa.ForeignKey("tipo_recomendacion.tipo_recomendacion_id"), nullable=False), sa.Column("recurrencia_id", sa.Integer(), sa.ForeignKey("recurrencia.recurrencia_id"), nullable=False))
    op.create_table("recurso", sa.Column("recurso_id", sa.Integer(), sa.Identity(always=True), primary_key=True), sa.Column("azure_resource_id", sa.String(2048), nullable=False), sa.Column("disparador_id", sa.Integer(), sa.ForeignKey("disparador.disparador_id"), nullable=False), sa.UniqueConstraint("azure_resource_id", name="uq_recurso_azure_resource_id"))
    op.create_table("reporte", sa.Column("reporte_id", sa.Integer(), sa.Identity(always=True), primary_key=True), sa.Column("periodo_mes", sa.SmallInteger(), nullable=False), sa.Column("periodo_anio", sa.SmallInteger(), nullable=False), sa.Column("inicio_generacion", sa.DateTime()), sa.Column("fin_generacion", sa.DateTime()), sa.Column("url_docx", sa.String(2048)), sa.Column("error_mensaje", sa.Text()), sa.Column("estado_reporte_id", sa.Integer(), sa.ForeignKey("estado_reporte.estado_reporte_id"), nullable=False), sa.Column("disparador_id", sa.Integer(), sa.ForeignKey("disparador.disparador_id"), nullable=False), sa.CheckConstraint("periodo_mes BETWEEN 1 AND 12", name="chk_reporte_periodo_mes"))

    for table, col in [("tenant", "cliente_id"), ("usuario", "rol_id"), ("disparador", "usuario_id"), ("disparador", "cliente_id"), ("disparador", "tipo_recomendacion_id"), ("disparador", "recurrencia_id"), ("recurso", "disparador_id"), ("reporte", "disparador_id"), ("reporte", "estado_reporte_id")]:
        op.create_index(f"idx_{table}_{col.replace('_id', '')}", table, [col])
    op.create_index("idx_reporte_periodo", "reporte", ["periodo_anio", "periodo_mes"])

    op.execute("INSERT INTO rol (nombre, descripcion) VALUES ('Administrador', 'Gestiona clientes y usuarios.'), ('Especialista', 'Genera reportes.')")
    op.execute("INSERT INTO tipo_recomendacion (nombre, descripcion) VALUES ('Alta', 'Recomendaciones solo de tipo alta.'), ('Media', 'Recomendaciones de prioridad alta y media.'), ('Baja', 'Recomendaciones de prioridad alta, media y baja.')")
    op.execute("INSERT INTO estado_reporte (nombre, descripcion) VALUES ('Pendiente', 'El reporte está pendiente de ejecución.'), ('En proceso', 'El reporte se encuentra en generación.'), ('Completado', 'El reporte fue generado exitosamente.'), ('Error', 'La generación del reporte finalizó con errores.')")
    op.execute("INSERT INTO recurrencia (nombre, descripcion) VALUES ('Única', 'El disparador se ejecuta una sola vez.'), ('Mensual', 'El disparador se ejecuta mensualmente.')")


def downgrade() -> None:
    op.drop_table("reporte")
    op.drop_table("recurso")
    op.drop_table("disparador")
    op.drop_table("usuario")
    op.drop_table("tenant")
    op.drop_table("cliente")
    op.drop_table("recurrencia")
    op.drop_table("estado_reporte")
    op.drop_table("tipo_recomendacion")
    op.drop_table("rol")
