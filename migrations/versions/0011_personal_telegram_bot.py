"""Encrypted personal bot credentials; no automatic selection or migration of tokens."""
from alembic import context, op
import sqlalchemy as sa

revision = '0011_personal_telegram_bot'
down_revision = '0010_explicit_public_bot'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('personal_telegram_bots',
        sa.Column('user_id',sa.String(36),sa.ForeignKey('auth_users.id'),primary_key=True),
        sa.Column('ciphertext',sa.String(2048),nullable=False),
        sa.Column('bot_id',sa.String(20),unique=True,nullable=False),
        sa.Column('username',sa.String(32),nullable=False),
        sa.Column('fingerprint',sa.String(64),unique=True,nullable=False),
        sa.Column('update_offset',sa.Integer(),nullable=False),
        sa.Column('lease_id',sa.String(36),nullable=True),
        sa.Column('lease_until',sa.DateTime(timezone=True),nullable=True))


def downgrade():
    bind=op.get_bind()
    if bind.scalar(sa.text('SELECT count(*) FROM personal_telegram_bots')):
        raise RuntimeError('Unlink personal bots before downgrade')
    if context.get_revision_argument()!=down_revision:
        if bind.scalar(sa.text('SELECT count(*) FROM account_notifications WHERE bot_mode IS NOT NULL OR chat_id IS NOT NULL OR enabled=true OR private_target=true')) or bind.scalar(sa.text('SELECT count(*) FROM telegram_challenges')):
            raise RuntimeError('Unlink all account notifications and cancel pairing before downgrade')
        if context.get_revision_argument() not in ('0009_account_notifications','0008_notifications'):
            if bind.scalar(sa.text("SELECT count(*) FROM notification_preferences WHERE enabled=true OR chat_id <> ''")):
                raise RuntimeError('Clear legacy notification preferences before downgrade')
        if context.get_revision_argument() not in ('0009_account_notifications','0008_notifications','0007_login_activity','0006_registration_policy'):
            if bind.scalar(sa.text('SELECT count(*) FROM registration_applications WHERE pending=true')):
                raise RuntimeError('Resolve pending registrations before downgrade')
    op.drop_table('personal_telegram_bots')
