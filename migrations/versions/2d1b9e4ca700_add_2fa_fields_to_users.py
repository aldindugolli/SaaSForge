"""add 2fa fields to users

Revision ID: 2d1b9e4ca700
Revises: 78e2f1f46958
Create Date: 2026-06-22 20:49:41.257370

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2d1b9e4ca700'
down_revision = '78e2f1f46958'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('totp_secret', sa.String(32), nullable=True))
    op.add_column('users', sa.Column('totp_enabled', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('users', sa.Column('totp_backup_codes', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('users', 'totp_backup_codes')
    op.drop_column('users', 'totp_enabled')
    op.drop_column('users', 'totp_secret')
