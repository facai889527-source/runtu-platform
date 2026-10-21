"""Explicit business-module grants and minimal grant audit; existing rows untouched."""
from alembic import op
import sqlalchemy as sa

revision = '0005_user_module_access'
down_revision = '0004_module_management'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('user_module_grants',
        sa.Column('user_id', sa.String(36), sa.ForeignKey('auth_users.id'), primary_key=True),
        sa.Column('module_id', sa.String(64), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.create_table('user_module_grant_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('actor_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('module_id', sa.String(64), nullable=False),
        sa.Column('action', sa.String(16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))


def downgrade():
    # Explicitly lossy for grants/audit only; never touches users or sessions.
    op.drop_table('user_module_grant_events')
    op.drop_table('user_module_grants')
