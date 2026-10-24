"""Add verified sender identity without clearing credentials, bindings or preferences."""
from alembic import context, op
import sqlalchemy as sa
revision='0013_telegram_identity'
down_revision='0012_owner_public_bot'
branch_labels=None
depends_on=None

def upgrade():
    for table in ('account_notifications','telegram_challenges'):
        for name,size in (('user_id',16),('first_name',64),('last_name',64),('username',32)):
            op.add_column(table,sa.Column('telegram_'+name,sa.String(size),nullable=True))
        # Existing proofs required private chat ID == immutable sender ID.
        op.execute(sa.text('UPDATE '+table+' SET telegram_user_id=chat_id WHERE chat_id IS NOT NULL'))

def downgrade():
    target=context.get_revision_argument()
    bind=op.get_bind()
    if target!=down_revision:
        if bind.scalar(sa.text('SELECT count(*) FROM telegram_platform WHERE enabled=true OR owner_id IS NOT NULL')):
            raise RuntimeError('Unlink owner public Bot and disable setup before downgrade')
        if target!='0011_personal_telegram_bot':
            if bind.scalar(sa.text('SELECT count(*) FROM personal_telegram_bots')):
                raise RuntimeError('Unlink personal bots before downgrade')
            if target!='0010_explicit_public_bot':
                if bind.scalar(sa.text('SELECT count(*) FROM account_notifications WHERE bot_mode IS NOT NULL OR chat_id IS NOT NULL OR enabled=true OR private_target=true')) or bind.scalar(sa.text('SELECT count(*) FROM telegram_challenges')):
                    raise RuntimeError('Unlink all account notifications and cancel pairing before downgrade')
                if target not in ('0009_account_notifications','0008_notifications'):
                    if bind.scalar(sa.text("SELECT count(*) FROM notification_preferences WHERE enabled=true OR chat_id <> ''")):
                        raise RuntimeError('Clear legacy notification preferences before downgrade')
                if target not in ('0009_account_notifications','0008_notifications','0007_login_activity','0006_registration_policy'):
                    if bind.scalar(sa.text('SELECT count(*) FROM registration_applications WHERE pending=true')):
                        raise RuntimeError('Resolve pending registrations before downgrade')
    # Names are optional metadata; retain all established binding/credential data.
    for table in ('telegram_challenges','account_notifications'):
        with op.batch_alter_table(table) as batch:
            for name in ('username','last_name','first_name','user_id'):
                batch.drop_column('telegram_'+name)
