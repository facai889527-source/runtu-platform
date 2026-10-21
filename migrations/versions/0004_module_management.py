"""Reviewable module state overrides, optimistic versions and non-secret audit."""
from alembic import op
import sqlalchemy as sa

revision = '0004_module_management'
down_revision = '0003_rbac_roles'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('module_configs') as batch:
        batch.add_column(sa.Column('enabled', sa.Boolean(), nullable=True))
        batch.add_column(sa.Column('revision', sa.Integer(), nullable=False, server_default='0'))
        batch.create_check_constraint('ck_module_configs_revision', 'revision >= 0')
    op.create_table('module_changes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('module_id', sa.String(64), nullable=False),
        sa.Column('actor_id', sa.String(36), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('module_id', 'revision', name='uq_module_changes_revision'))


def downgrade():
    op.drop_table('module_changes')
    with op.batch_alter_table('module_configs') as batch:
        batch.drop_constraint('ck_module_configs_revision', type_='check')
        batch.drop_column('revision')
        batch.drop_column('enabled')
