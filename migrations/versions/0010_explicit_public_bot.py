"""Explicit public-bot choice and private destination opt-in; no implicit migration binding."""
from alembic import context, op
import sqlalchemy as sa

revision = '0010_explicit_public_bot'
down_revision = '0009_account_notifications'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('account_notifications', sa.Column('bot_mode', sa.String(8), nullable=True))
    op.add_column('account_notifications', sa.Column('bot_key', sa.String(64), nullable=True))
    op.add_column('account_notifications', sa.Column('private_target', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('telegram_challenges', sa.Column('initiator_id', sa.String(36), nullable=True))
    # Existing private bindings do not authorize a bot mode or target selection.
    op.execute(sa.text('DELETE FROM telegram_challenges'))
    op.execute(sa.text('UPDATE account_notifications SET chat_id=NULL, bound_at=NULL, enabled=false, registration=false, paused=false, revision=revision+1'))


def downgrade():
    bind = op.get_bind()
    if bind.scalar(sa.text('SELECT count(*) FROM account_notifications WHERE bot_mode IS NOT NULL OR chat_id IS NOT NULL OR enabled=true OR private_target=true')) or bind.scalar(sa.text('SELECT count(*) FROM telegram_challenges')):
        raise RuntimeError('Unlink all account notifications and cancel pairing before downgrade')
    target = context.get_revision_argument()
    if target not in (down_revision, '0008_notifications'):
        if bind.scalar(sa.text("SELECT count(*) FROM notification_preferences WHERE enabled=true OR chat_id <> ''")):
            raise RuntimeError('Clear legacy notification preferences before downgrade')
    if target not in (down_revision, '0008_notifications', '0007_login_activity', '0006_registration_policy'):
        if bind.scalar(sa.text('SELECT count(*) FROM registration_applications WHERE pending=true')):
            raise RuntimeError('Resolve pending registrations before downgrade')
    with op.batch_alter_table('telegram_challenges') as batch:
        batch.drop_column('initiator_id')
    with op.batch_alter_table('account_notifications') as batch:
        batch.drop_column('private_target')
        batch.drop_column('bot_key')
        batch.drop_column('bot_mode')
