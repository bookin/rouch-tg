"""add_timezone_to_all_datetime_columns

Revision ID: 417d3acb4b9b
Revises: 399c45a5f97c
Create Date: 2026-03-01 01:28:47.540982+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '417d3acb4b9b'
down_revision: Union[str, None] = '399c45a5f97c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Convert partners.last_action_date from TIMESTAMP to TIMESTAMPTZ
    op.alter_column('partners', 'last_action_date',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               postgresql_using="last_action_date AT TIME ZONE 'UTC'")

    # 2. Fill NULL values with defaults before adding NOT NULL constraints
    op.execute("UPDATE seeds SET rejoice_count = 0 WHERE rejoice_count IS NULL")
    op.execute("UPDATE seeds SET intention_score = 5 WHERE intention_score IS NULL")
    op.execute("UPDATE seeds SET emotion_level = 5 WHERE emotion_level IS NULL")
    op.execute("UPDATE seeds SET understanding = false WHERE understanding IS NULL")
    op.execute("UPDATE seeds SET estimated_maturation_days = 21 WHERE estimated_maturation_days IS NULL")
    op.execute("UPDATE seeds SET strength_multiplier = 1.0 WHERE strength_multiplier IS NULL")
    op.execute("UPDATE users SET streak_days = 0 WHERE streak_days IS NULL")
    op.execute("UPDATE users SET total_seeds = 0 WHERE total_seeds IS NULL")
    op.execute("UPDATE users SET completed_practices = 0 WHERE completed_practices IS NULL")
    op.execute("UPDATE users SET timezone = 'UTC' WHERE timezone IS NULL")
    op.execute("UPDATE users SET morning_enabled = true WHERE morning_enabled IS NULL")
    op.execute("UPDATE users SET evening_enabled = true WHERE evening_enabled IS NULL")
    op.execute("UPDATE coffee_meditation_sessions SET current_step = 0 WHERE current_step IS NULL")
    op.execute("UPDATE daily_plans SET is_completed = false WHERE is_completed IS NULL")
    op.execute("UPDATE daily_tasks SET completed = false WHERE completed IS NULL")
    op.execute("UPDATE daily_tasks SET \"order\" = 0 WHERE \"order\" IS NULL")
    op.execute("UPDATE karma_plans SET duration_days = 30 WHERE duration_days IS NULL")
    op.execute("UPDATE partner_actions SET completed = false WHERE completed IS NULL")
    op.execute("UPDATE partner_groups SET is_default = false WHERE is_default IS NULL")
    op.execute("UPDATE partners SET seeds_count = 0 WHERE seeds_count IS NULL")
    op.execute("UPDATE practice_progress SET habit_score = 0 WHERE habit_score IS NULL")
    op.execute("UPDATE practice_progress SET streak_days = 0 WHERE streak_days IS NULL")
    op.execute("UPDATE practice_progress SET total_completions = 0 WHERE total_completions IS NULL")
    op.execute("UPDATE practice_progress SET is_habit = false WHERE is_habit IS NULL")
    op.execute("UPDATE practice_progress SET is_active = true WHERE is_active IS NULL")
    op.execute("UPDATE practice_progress SET is_hidden = false WHERE is_hidden IS NULL")
    op.execute("UPDATE practices SET requires_morning = false WHERE requires_morning IS NULL")
    op.execute("UPDATE practices SET requires_silence = false WHERE requires_silence IS NULL")
    op.execute("UPDATE practices SET difficulty = 1 WHERE difficulty IS NULL")
    op.execute("UPDATE practices SET max_completions_per_day = 1 WHERE max_completions_per_day IS NULL")
    op.execute("UPDATE practices SET habit_min_streak_days = 14 WHERE habit_min_streak_days IS NULL")
    op.execute("UPDATE practices SET habit_min_score = 70 WHERE habit_min_score IS NULL")

    # 3. Add NOT NULL constraints
    op.alter_column('coffee_meditation_sessions', 'current_step',
               existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('daily_plans', 'is_completed',
               existing_type=sa.BOOLEAN(), nullable=False)
    op.alter_column('daily_tasks', 'completed',
               existing_type=sa.BOOLEAN(), nullable=False)
    op.alter_column('daily_tasks', 'order',
               existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('karma_plans', 'duration_days',
               existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('partner_actions', 'completed',
               existing_type=sa.BOOLEAN(), nullable=False)
    op.alter_column('partner_groups', 'is_default',
               existing_type=sa.BOOLEAN(), nullable=False)
    op.alter_column('partners', 'seeds_count',
               existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('practice_progress', 'habit_score',
               existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('practice_progress', 'streak_days',
               existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('practice_progress', 'total_completions',
               existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('practice_progress', 'is_habit',
               existing_type=sa.BOOLEAN(), nullable=False)
    op.alter_column('practice_progress', 'is_active',
               existing_type=sa.BOOLEAN(), server_default=None, nullable=False)
    op.alter_column('practice_progress', 'is_hidden',
               existing_type=sa.BOOLEAN(), server_default=None, nullable=False)
    op.alter_column('practices', 'requires_morning',
               existing_type=sa.BOOLEAN(), nullable=False)
    op.alter_column('practices', 'requires_silence',
               existing_type=sa.BOOLEAN(), nullable=False)
    op.alter_column('practices', 'difficulty',
               existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('practices', 'max_completions_per_day',
               existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('practices', 'habit_min_streak_days',
               existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('practices', 'habit_min_score',
               existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('seeds', 'intention_score',
               existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('seeds', 'emotion_level',
               existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('seeds', 'understanding',
               existing_type=sa.BOOLEAN(), nullable=False)
    op.alter_column('seeds', 'estimated_maturation_days',
               existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('seeds', 'strength_multiplier',
               existing_type=sa.DOUBLE_PRECISION(precision=53), nullable=False)
    op.alter_column('seeds', 'rejoice_count',
               existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('seeds', 'daily_task_id',
               existing_type=sa.INTEGER(), type_=sa.BigInteger(), existing_nullable=True)
    op.alter_column('users', 'streak_days',
               existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('users', 'total_seeds',
               existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('users', 'completed_practices',
               existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('users', 'timezone',
               existing_type=sa.VARCHAR(), nullable=False)
    op.alter_column('users', 'morning_enabled',
               existing_type=sa.BOOLEAN(), nullable=False)
    op.alter_column('users', 'evening_enabled',
               existing_type=sa.BOOLEAN(), nullable=False)


def downgrade() -> None:
    op.alter_column('users', 'evening_enabled',
               existing_type=sa.BOOLEAN(), nullable=True)
    op.alter_column('users', 'morning_enabled',
               existing_type=sa.BOOLEAN(), nullable=True)
    op.alter_column('users', 'timezone',
               existing_type=sa.VARCHAR(), nullable=True)
    op.alter_column('users', 'completed_practices',
               existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('users', 'total_seeds',
               existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('users', 'streak_days',
               existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('seeds', 'daily_task_id',
               existing_type=sa.BigInteger(), type_=sa.INTEGER(), existing_nullable=True)
    op.alter_column('seeds', 'rejoice_count',
               existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('seeds', 'strength_multiplier',
               existing_type=sa.DOUBLE_PRECISION(precision=53), nullable=True)
    op.alter_column('seeds', 'estimated_maturation_days',
               existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('seeds', 'understanding',
               existing_type=sa.BOOLEAN(), nullable=True)
    op.alter_column('seeds', 'emotion_level',
               existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('seeds', 'intention_score',
               existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('practices', 'habit_min_score',
               existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('practices', 'habit_min_streak_days',
               existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('practices', 'max_completions_per_day',
               existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('practices', 'difficulty',
               existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('practices', 'requires_silence',
               existing_type=sa.BOOLEAN(), nullable=True)
    op.alter_column('practices', 'requires_morning',
               existing_type=sa.BOOLEAN(), nullable=True)
    op.alter_column('practice_progress', 'is_hidden',
               existing_type=sa.BOOLEAN(), server_default=sa.text('false'), nullable=True)
    op.alter_column('practice_progress', 'is_active',
               existing_type=sa.BOOLEAN(), server_default=sa.text('true'), nullable=True)
    op.alter_column('practice_progress', 'is_habit',
               existing_type=sa.BOOLEAN(), nullable=True)
    op.alter_column('practice_progress', 'total_completions',
               existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('practice_progress', 'streak_days',
               existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('practice_progress', 'habit_score',
               existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('partners', 'last_action_date',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(), existing_nullable=True)
    op.alter_column('partners', 'seeds_count',
               existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('partner_groups', 'is_default',
               existing_type=sa.BOOLEAN(), nullable=True)
    op.alter_column('partner_actions', 'completed',
               existing_type=sa.BOOLEAN(), nullable=True)
    op.alter_column('karma_plans', 'duration_days',
               existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('daily_tasks', 'order',
               existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('daily_tasks', 'completed',
               existing_type=sa.BOOLEAN(), nullable=True)
    op.alter_column('daily_plans', 'is_completed',
               existing_type=sa.BOOLEAN(), nullable=True)
    op.alter_column('coffee_meditation_sessions', 'current_step',
               existing_type=sa.INTEGER(), nullable=True)
