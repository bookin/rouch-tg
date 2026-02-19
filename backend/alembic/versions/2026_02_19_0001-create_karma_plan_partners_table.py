"""create karma_plan_partners table

Revision ID: 2026_02_19_0001
Revises: 2026_02_19_0000
Create Date: 2026-02-19 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2026_02_19_0001'
down_revision: Union[str, None] = '2026_02_19_0000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create karma_plan_partners table
    op.create_table(
        'karma_plan_partners',
        sa.Column('plan_id', sa.String(), nullable=False),
        sa.Column('partner_id', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['partner_id'], ['partners.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_id'], ['karma_plans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('plan_id', 'partner_id', 'category')
    )

    # Migrate data from project_partners JSON to karma_plan_partners table
    # This assumes project_partners is {category: [partner_ids]}
    
    # We need to execute raw SQL for data migration
    connection = op.get_bind()
    
    # Select all plans with project_partners
    plans = connection.execute(sa.text("SELECT id, project_partners FROM karma_plans WHERE project_partners IS NOT NULL"))
    
    for plan in plans:
        plan_id = plan[0]
        partners_json = plan[1]
        
        if not partners_json:
            continue
            
        # Iterate through categories and partner IDs
        for category, partner_ids in partners_json.items():
            if not partner_ids:
                continue
                
            for partner_id in partner_ids:
                # Insert into new table
                # Check if partner exists first to avoid FK errors (though they should exist)
                partner_exists = connection.execute(sa.text(f"SELECT 1 FROM partners WHERE id = '{partner_id}'")).scalar()
                
                if partner_exists:
                    connection.execute(
                        sa.text("INSERT INTO karma_plan_partners (plan_id, partner_id, category) VALUES (:plan_id, :partner_id, :category)"),
                        {"plan_id": plan_id, "partner_id": partner_id, "category": category}
                    )

    # Drop project_partners column from karma_plans
    op.drop_column('karma_plans', 'project_partners')


def downgrade() -> None:
    # Add project_partners column back to karma_plans
    op.add_column('karma_plans', sa.Column('project_partners', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True))
    
    # Migrate data back (reverse logic - simplified)
    # We aggregate partners back into JSON
    connection = op.get_bind()
    
    # Get all plans from relation table
    rows = connection.execute(sa.text("SELECT plan_id, partner_id, category FROM karma_plan_partners"))
    
    plan_map = {}
    for row in rows:
        plan_id = row[0]
        partner_id = row[1]
        category = row[2]
        
        if plan_id not in plan_map:
            plan_map[plan_id] = {}
            
        if category not in plan_map[plan_id]:
            plan_map[plan_id][category] = []
            
        plan_map[plan_id][category].append(partner_id)
    
    # Update karma_plans
    for plan_id, partners_json in plan_map.items():
        # Convert dict to json string in SQL? No, we can pass as parameter if using sqlalchemy properly or driver handles it
        # Using simple update with parameter
        import json
        json_data = json.dumps(partners_json)
        connection.execute(
            sa.text(f"UPDATE karma_plans SET project_partners = '{json_data}' WHERE id = '{plan_id}'")
        )

    # Drop karma_plan_partners table
    op.drop_table('karma_plan_partners')
