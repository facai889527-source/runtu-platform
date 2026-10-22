"""Disabled-by-default registration and explicit approval markers."""
from alembic import op
import sqlalchemy as sa

revision = '0006_registration_policy'
down_revision = '0005_user_module_access'
branch_labels = None
depends_on = None


def upgrade():
    policy = op.create_table('registration_policy',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('approval_required', sa.Boolean(), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.CheckConstraint('id = 1', name='ck_registration_policy_singleton'),
        sa.CheckConstraint('revision >= 0', name='ck_registration_policy_revision'))
    op.bulk_insert(policy, [dict(id=1, enabled=False, approval_required=True, revision=0)])
    op.create_table('registration_applications',
        sa.Column('user_id', sa.String(36), sa.ForeignKey('auth_users.id'), primary_key=True),
        sa.Column('pending', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))


def downgrade():
    # Old application versions do not understand approval markers. Refuse unsafe loss.
    pending = sa.table('registration_applications', sa.column('pending', sa.Boolean()))
    if op.get_bind().scalar(sa.select(sa.func.count()).select_from(pending).where(pending.c.pending.is_(True))):
        raise RuntimeError('Resolve pending registrations before downgrade')
    op.drop_table('registration_applications')
    op.drop_table('registration_policy')
