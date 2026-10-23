"""Nonsecret Telegram preferences only; credentials remain environment-managed."""
from alembic import context, op
import sqlalchemy as sa

revision = '0008_notifications'
down_revision = '0007_login_activity'
branch_labels = None
depends_on = None


def upgrade():
    table = op.create_table('notification_preferences',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('chat_id', sa.String(21), nullable=False),
        sa.Column('registration', sa.Boolean(), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.CheckConstraint('id = 1', name='ck_notification_singleton'),
        sa.CheckConstraint('revision >= 0', name='ck_notification_revision'))
    op.bulk_insert(table, [dict(id=1, enabled=False, chat_id='', registration=False, revision=0)])


def downgrade():
    table = sa.table('notification_preferences', sa.column('enabled'), sa.column('chat_id'))
    if op.get_bind().scalar(sa.select(sa.func.count()).select_from(table).where(
            sa.or_(table.c.enabled.is_(True), table.c.chat_id != ''))):
        raise RuntimeError('Disable and clear notification preferences before downgrade')
    # Refuse before SQLite DDL if a later registration downgrade would refuse.
    if context.get_revision_argument() not in (down_revision, '0006_registration_policy'):
        pending = sa.table('registration_applications', sa.column('pending', sa.Boolean()))
        if op.get_bind().scalar(sa.select(sa.func.count()).select_from(pending).where(pending.c.pending.is_(True))):
            raise RuntimeError('Resolve pending registrations before downgrade')
    op.drop_table('notification_preferences')
