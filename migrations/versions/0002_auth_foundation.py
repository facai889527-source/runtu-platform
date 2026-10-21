"""Administrator identity, hashed sessions, bounded attempts and safe audit metadata."""
from alembic import op
import sqlalchemy as sa

revision = "0002_auth_foundation"
down_revision = "0001_module_configs"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("auth_users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("auth_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("auth_users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])
    op.create_table("auth_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event", sa.String(32), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_auth_events_created_at", "auth_events", ["created_at"])
    op.create_table("auth_rate_limits",
        sa.Column("bucket", sa.String(64), primary_key=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("reset_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_auth_rate_limits_reset_at", "auth_rate_limits", ["reset_at"])
    op.create_table("auth_bootstrap",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_auth_bootstrap_singleton"))


def downgrade():
    # Explicit destructive operator action: revokes all sessions and removes identities/audit.
    for table in ("auth_bootstrap", "auth_rate_limits", "auth_events", "auth_sessions", "auth_users"):
        op.drop_table(table)
