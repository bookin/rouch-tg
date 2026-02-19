"""add universal partner fields

Revision ID: 2026_02_19_0000
Revises: 2026_02_09_0000
Create Date: 2026-02-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_02_19_0000'
down_revision: Union[str, None] = '2026_02_09_0000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add universal_category to partner_groups
    op.add_column('partner_groups', sa.Column('universal_category', sa.String(), nullable=True))
    
    # Update categories and RENAME groups to Universal Model
    # Source
    op.execute("UPDATE partner_groups SET universal_category = 'source', name = 'Source', icon = '🙌', description = 'Кто дает ресурсы (Родители, учителя, поставщики)' WHERE name = 'Поставщики'")
    # Ally
    op.execute("UPDATE partner_groups SET universal_category = 'ally', name = 'Ally', icon = '🤝', description = 'Кто помогает в делах (Коллеги, партнеры)' WHERE name = 'Коллеги'")
    # Protege
    op.execute("UPDATE partner_groups SET universal_category = 'protege', name = 'Protege', icon = '🌱', description = 'Кто зависит от тебя (Клиенты, дети, подчиненные)' WHERE name = 'Клиенты'")
    # World
    op.execute("UPDATE partner_groups SET universal_category = 'world', name = 'World', icon = '🌍', description = 'Незнакомцы, конкуренты, общество' WHERE name = 'Мир'")
    
    # Set default for others
    op.execute("UPDATE partner_groups SET universal_category = 'world' WHERE universal_category IS NULL")

    # Add project_partners to karma_plans
    op.add_column('karma_plans', sa.Column('project_partners', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove project_partners from karma_plans
    op.drop_column('karma_plans', 'project_partners')
    
    # Revert group names (optional, but good for completeness)
    op.execute("UPDATE partner_groups SET name = 'Поставщики' WHERE universal_category = 'source'")
    op.execute("UPDATE partner_groups SET name = 'Коллеги' WHERE universal_category = 'ally'")
    op.execute("UPDATE partner_groups SET name = 'Клиенты' WHERE universal_category = 'protege'")
    op.execute("UPDATE partner_groups SET name = 'Мир' WHERE universal_category = 'world'")

    # Remove universal_category from partner_groups
    op.drop_column('partner_groups', 'universal_category')
