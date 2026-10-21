"""Fixed roles; migrate legacy administrators without anonymous privilege grants."""
from alembic import op
import sqlalchemy as sa

revision = '0003_rbac_roles'
down_revision = '0002_auth_foundation'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('DELETE FROM auth_sessions')
    # Explicit nullable phase allows a deterministic backfill before NOT NULL.
    op.add_column('auth_users', sa.Column('role', sa.String(16), nullable=True))
    op.execute("UPDATE auth_users SET role = CASE WHEN is_admin THEN 'owner' ELSE 'viewer' END")
    with op.batch_alter_table('auth_users') as batch:
        batch.alter_column('role', existing_type=sa.String(16), nullable=False)
        batch.create_check_constraint('ck_auth_users_role', "role IN ('owner', 'admin', 'viewer')")


def downgrade():
    # Prevent an old is_admin=True marker from resurrecting a demoted user's authority.
    # Legacy boolean cannot express admin's narrower scope: conservatively retain only owners.
    op.execute("UPDATE auth_users SET is_admin = CASE WHEN role = 'owner' THEN TRUE ELSE FALSE END")
    op.execute('DELETE FROM auth_sessions')
    with op.batch_alter_table('auth_users') as batch:
        batch.drop_constraint('ck_auth_users_role', type_='check')
        batch.drop_column('role')
