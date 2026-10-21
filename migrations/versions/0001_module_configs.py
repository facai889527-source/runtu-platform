"""Initial non-sensitive module configuration schema."""
from alembic import op
import sqlalchemy as sa

revision = "0001_module_configs"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "module_configs",
        sa.Column("module_id", sa.String(64), primary_key=True),
        sa.Column("show_in_navigation", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("refresh_interval_seconds", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "refresh_interval_seconds IS NULL OR "
            "(refresh_interval_seconds >= 1 AND refresh_interval_seconds <= 86400)",
            name="ck_module_configs_refresh_interval",
        ),
    )


def downgrade():
    op.drop_table("module_configs")
