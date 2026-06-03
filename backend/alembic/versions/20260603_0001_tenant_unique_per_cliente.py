"""Scope Azure tenant uniqueness per client.

Revision ID: 20260603_0001
Revises:
Create Date: 2026-06-03
"""

from alembic import op


revision = "20260603_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE tenants DROP CONSTRAINT IF EXISTS uq_tenants_tenant_id_azure")
    op.execute("ALTER TABLE tenants DROP CONSTRAINT IF EXISTS tenants_tenant_id_azure_key")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_tenants_cliente_id_tenant_id_azure'
            ) THEN
                ALTER TABLE tenants
                ADD CONSTRAINT uq_tenants_cliente_id_tenant_id_azure
                UNIQUE (cliente_id, tenant_id_azure);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE tenants "
        "DROP CONSTRAINT IF EXISTS uq_tenants_cliente_id_tenant_id_azure"
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_tenants_tenant_id_azure'
            ) THEN
                ALTER TABLE tenants
                ADD CONSTRAINT uq_tenants_tenant_id_azure
                UNIQUE (tenant_id_azure);
            END IF;
        END $$;
        """
    )
