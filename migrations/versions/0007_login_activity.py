"""Reuse auth audit for session-specific previous successful login."""
from alembic import context, op
import sqlalchemy as sa

revision = '0007_login_activity'
down_revision = '0006_registration_policy'
branch_labels = None
depends_on = None


def upgrade():
    # Reuse legacy successful timestamps; their hashed source cannot yield an IP.
    op.add_column('auth_events', sa.Column('source_ip', sa.String(45), nullable=True))
    op.add_column('auth_users', sa.Column('last_login_event_id', sa.String(36), nullable=True))
    op.add_column('auth_sessions', sa.Column('previous_login_event_id', sa.String(36), nullable=True))

    events = sa.table('auth_events', sa.column('id'), sa.column('user_id'), sa.column('event'), sa.column('created_at'))
    users = sa.table('auth_users', sa.column('id'), sa.column('last_login_event_id'))
    sessions = sa.table('auth_sessions', sa.column('user_id'), sa.column('created_at'), sa.column('previous_login_event_id'))
    latest = sa.select(events.c.id).where(events.c.user_id == users.c.id,
        events.c.event == 'login_success').order_by(events.c.created_at.desc(), events.c.id.desc()).limit(1).scalar_subquery()
    op.get_bind().execute(users.update().values(last_login_event_id=latest))
    # A strict boundary excludes the current login, even when timestamps tie.
    boundary = events.c.created_at < sessions.c.created_at
    if op.get_bind().dialect.name == 'sqlite':
        # Normalize legacy timestamp representations; equal instants must never
        # become previous just because one string includes fractional zeros.
        boundary = sa.func.julianday(events.c.created_at) < sa.func.julianday(sessions.c.created_at)
    previous = sa.select(events.c.id).where(events.c.user_id == sessions.c.user_id,
        events.c.event == 'login_success', boundary
        ).order_by(events.c.created_at.desc(), events.c.id.desc()).limit(1).scalar_subquery()
    op.get_bind().execute(sessions.update().values(previous_login_event_id=previous))


def downgrade():
    # Preflight the existing 0006 guard before any SQLite DDL, which may not
    # roll back when a later migration refuses a multi-revision downgrade.
    if context.get_revision_argument() != down_revision:
        pending = sa.table('registration_applications', sa.column('pending', sa.Boolean()))
        if op.get_bind().scalar(sa.select(sa.func.count()).select_from(pending).where(pending.c.pending.is_(True))):
            raise RuntimeError('Resolve pending registrations before downgrade')
    op.drop_column('auth_sessions', 'previous_login_event_id')
    op.drop_column('auth_users', 'last_login_event_id')
    op.drop_column('auth_events', 'source_ip')
