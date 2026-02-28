"""hybrid_auth_fastapi_users

Revision ID: 32bd8f5aeb59
Revises: c5b53de4dc19
Create Date: 2026-02-28 03:45:47.213481+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32bd8f5aeb59'
down_revision: Union[str, None] = 'c5b53de4dc19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add auth columns for hybrid auth (fastapi-users)
    op.add_column('users', sa.Column('email', sa.String(length=320), nullable=True))
    op.add_column('users', sa.Column('hashed_password', sa.String(length=1024), nullable=True))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('users', sa.Column('is_superuser', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    # telegram_id becomes nullable (web users don't have it)
    op.alter_column('users', 'telegram_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.alter_column('users', 'telegram_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.drop_column('users', 'is_verified')
    op.drop_column('users', 'is_superuser')
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'hashed_password')
    op.drop_column('users', 'email')
