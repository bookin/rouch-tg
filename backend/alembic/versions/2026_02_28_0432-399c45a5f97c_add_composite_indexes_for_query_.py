"""add_composite_indexes_for_query_optimization

Revision ID: 399c45a5f97c
Revises: 32bd8f5aeb59
Create Date: 2026-02-28 04:32:12.837575+00:00

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '399c45a5f97c'
down_revision: Union[str, None] = '32bd8f5aeb59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('idx_seeds_user_timestamp', 'seeds', ['user_id', 'timestamp'], unique=False)
    op.create_index('idx_seeds_user_daily_task', 'seeds', ['user_id', 'daily_task_id'], unique=False)
    op.create_index('idx_seeds_user_practice_timestamp', 'seeds', ['user_id', 'practice_id', 'timestamp'], unique=False)
    op.create_index('idx_partner_groups_user_category_default', 'partner_groups', ['user_id', 'universal_category', 'is_default'], unique=False)
    op.create_index('idx_karma_plans_user_status', 'karma_plans', ['user_id', 'status'], unique=False)
    op.create_index('idx_daily_plans_karma_plan_date', 'daily_plans', ['karma_plan_id', 'date'], unique=False)
    op.create_index('idx_message_logs_user_type_channel_sent', 'message_logs', ['user_id', 'message_type', 'channel', 'sent_at'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_message_logs_user_type_channel_sent', table_name='message_logs')
    op.drop_index('idx_daily_plans_karma_plan_date', table_name='daily_plans')
    op.drop_index('idx_karma_plans_user_status', table_name='karma_plans')
    op.drop_index('idx_partner_groups_user_category_default', table_name='partner_groups')
    op.drop_index('idx_seeds_user_practice_timestamp', table_name='seeds')
    op.drop_index('idx_seeds_user_daily_task', table_name='seeds')
    op.drop_index('idx_seeds_user_timestamp', table_name='seeds')
