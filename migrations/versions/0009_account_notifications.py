"""Private verified bindings; never copy singleton destinations into accounts."""
from alembic import op
import sqlalchemy as sa

revision = '0009_account_notifications'
down_revision = '0008_notifications'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('account_notifications',
        sa.Column('user_id', sa.String(36), sa.ForeignKey('auth_users.id'), primary_key=True),
        sa.Column('chat_id', sa.String(16), unique=True, nullable=True),
        sa.Column('bound_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('registration', sa.Boolean(), nullable=False),
        sa.Column('paused', sa.Boolean(), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('revision >= 0', name='ck_account_notification_revision'))
    op.create_table('telegram_challenges',
        sa.Column('user_id', sa.String(36), sa.ForeignKey('auth_users.id'), primary_key=True),
        sa.Column('token_hash', sa.String(64), unique=True, nullable=True),
        sa.Column('session_hash', sa.String(64), nullable=False),
        sa.Column('chat_id', sa.String(16), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False))
    op.create_table('notification_deliveries',
        sa.Column('event_id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('auth_users.id'), primary_key=True),
        sa.Column('binding_revision', sa.Integer(), nullable=False),
        sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=False))
    # Quarantine the old destination for explicit operator review, and disable
    # its subscriptions so rolling back code cannot silently resume global sends.
    legacy = sa.table('notification_preferences', sa.column('enabled', sa.Boolean()),
        sa.column('registration', sa.Boolean()), sa.column('revision', sa.Integer()))
    op.get_bind().execute(legacy.update().where(sa.or_(legacy.c.enabled.is_(True),
        legacy.c.registration.is_(True))).values(enabled=False, registration=False, revision=legacy.c.revision+1))
    # No account gets the legacy destination or subscriptions.


def downgrade():
    profiles = sa.table('account_notifications', sa.column('chat_id'), sa.column('enabled', sa.Boolean()))
    challenges = sa.table('telegram_challenges', sa.column('user_id'))
    if op.get_bind().scalar(sa.select(sa.func.count()).select_from(profiles).where(
            sa.or_(profiles.c.chat_id.is_not(None), profiles.c.enabled.is_(True)))) or op.get_bind().scalar(
            sa.select(sa.func.count()).select_from(challenges)):
        raise RuntimeError('Unlink all account notifications and cancel pairing before downgrade')
    # Check earlier guards before SQLite DDL in a multi-revision downgrade.
    from alembic import context
    target = context.get_revision_argument()
    if target != down_revision:
        legacy = sa.table('notification_preferences', sa.column('enabled', sa.Boolean()), sa.column('chat_id'))
        if op.get_bind().scalar(sa.select(sa.func.count()).select_from(legacy).where(
                sa.or_(legacy.c.enabled.is_(True), legacy.c.chat_id != ''))):
            raise RuntimeError('Clear legacy notification preferences before downgrade')
    if target not in (down_revision, '0007_login_activity', '0006_registration_policy'):
        applications = sa.table('registration_applications', sa.column('pending', sa.Boolean()))
        if op.get_bind().scalar(sa.select(sa.func.count()).select_from(applications).where(applications.c.pending.is_(True))):
            raise RuntimeError('Resolve pending registrations before downgrade')
    op.drop_table('notification_deliveries')
    op.drop_table('telegram_challenges')
    op.drop_table('account_notifications')
