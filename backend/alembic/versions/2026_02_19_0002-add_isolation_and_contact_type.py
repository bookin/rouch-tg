"""add_isolation_and_contact_type

Revision ID: 2026_02_19_0002
Revises: 2026_02_19_0001
Create Date: 2026-02-19 19:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_02_19_0002'
down_revision: Union[str, None] = '2026_02_19_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add contact_type column to partners table
    op.add_column('partners', sa.Column('contact_type', sa.String(), server_default='physical', nullable=True))
    
    # Add isolation_settings column to karma_plans table
    op.add_column('karma_plans', sa.Column('isolation_settings', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove isolation_settings column from karma_plans table
    op.drop_column('karma_plans', 'isolation_settings')
    
    # Remove contact_type column from partners table
    op.drop_column('partners', 'contact_type')
