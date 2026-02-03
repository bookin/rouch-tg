"""Initial schema migration.

Creates all core tables used by the application.
"""

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision = "20260129_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("telegram_id", sa.Integer(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("occupation", sa.String(), nullable=True),
        sa.Column("available_times", sa.JSON(), nullable=True),
        sa.Column("daily_minutes", sa.Integer(), nullable=True),
        sa.Column("current_habits", sa.JSON(), nullable=True),
        sa.Column("physical_restrictions", sa.String(), nullable=True),
        sa.Column("streak_days", sa.Integer(), nullable=True),
        sa.Column("total_seeds", sa.Integer(), nullable=True),
        sa.Column("completed_practices", sa.Integer(), nullable=True),
        sa.Column("timezone", sa.String(), nullable=True),
        sa.Column("morning_enabled", sa.Boolean(), nullable=True),
        sa.Column("evening_enabled", sa.Boolean(), nullable=True),
        sa.Column("current_focus", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("last_onboarding_update", sa.DateTime(), nullable=True),
        sa.Column("last_morning_message", sa.DateTime(), nullable=True),
        sa.Column("last_evening_message", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "partner_groups",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("icon", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "partners",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("group_id", sa.String(), sa.ForeignKey("partner_groups.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("preferences", sa.JSON(), nullable=True),
        sa.Column("important_dates", sa.JSON(), nullable=True),
        sa.Column("seeds_count", sa.Integer(), nullable=True),
        sa.Column("last_action_date", sa.DateTime(), nullable=True),
        sa.Column("telegram_username", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "practices",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("requires_morning", sa.Boolean(), nullable=True),
        sa.Column("requires_silence", sa.Boolean(), nullable=True),
        sa.Column("physical_intensity", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
    )

    op.create_table(
        "habits",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("practice_id", sa.String(), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("frequency", sa.String(), nullable=True),
        sa.Column("preferred_time", sa.String(), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("streak", sa.Integer(), nullable=True),
        sa.Column("last_completed", sa.DateTime(), nullable=True),
        sa.Column("completion_rate", sa.Float(), nullable=True),
        sa.Column("user_restrictions", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
    )

    op.create_table(
        "seeds",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "partner_id",
            sa.String(),
            sa.ForeignKey("partners.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("partner_group", sa.String(), nullable=True),
        sa.Column("intention_score", sa.Integer(), nullable=True),
        sa.Column("emotion_level", sa.Integer(), nullable=True),
        sa.Column("understanding", sa.Boolean(), nullable=True),
        sa.Column("estimated_maturation_days", sa.Integer(), nullable=True),
        sa.Column("strength_multiplier", sa.Float(), nullable=True),
    )
    op.create_index("ix_seeds_user_id", "seeds", ["user_id"])
    op.create_index("ix_seeds_timestamp", "seeds", ["timestamp"])
    op.create_index("ix_seeds_action_type", "seeds", ["action_type"])

    op.create_table(
        "habit_completions",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column("habit_id", sa.String(), sa.ForeignKey("habits.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_actual", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    op.create_table(
        "partner_actions",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "partner_id",
            sa.String(),
            sa.ForeignKey("partners.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("partner_name", sa.String(), nullable=True),
        sa.Column("seed_id", sa.String(), sa.ForeignKey("seeds.id"), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=True),
    )
    op.create_index("ix_partner_actions_timestamp", "partner_actions", ["timestamp"])
    op.create_index("ix_partner_actions_completed", "partner_actions", ["completed"])

    # LangGraph checkpointing tables (optional, but included since models exist)
    op.create_table(
        "checkpoints",
        sa.Column("thread_id", sa.String(), nullable=False),
        sa.Column("checkpoint_id", sa.String(), nullable=False),
        sa.Column("parent_checkpoint_id", sa.String(), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("checkpoint", sa.LargeBinary(), nullable=False),
        sa.Column("metadata", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("thread_id", "checkpoint_id"),
    )

    op.create_table(
        "checkpoint_blobs",
        sa.Column("thread_id", sa.String(), nullable=False),
        sa.Column("checkpoint_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("blob", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("thread_id", "checkpoint_id", "type"),
    )

    op.create_table(
        "checkpoint_writes",
        sa.Column("thread_id", sa.String(), nullable=False),
        sa.Column("checkpoint_id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("idx", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("blob", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("thread_id", "checkpoint_id", "task_id", "idx"),
    )


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_table("checkpoint_writes")
    op.drop_table("checkpoint_blobs")
    op.drop_table("checkpoints")
    op.drop_index("ix_partner_actions_completed", table_name="partner_actions")
    op.drop_index("ix_partner_actions_timestamp", table_name="partner_actions")
    op.drop_table("partner_actions")
    op.drop_table("habit_completions")
    op.drop_index("ix_seeds_action_type", table_name="seeds")
    op.drop_index("ix_seeds_timestamp", table_name="seeds")
    op.drop_index("ix_seeds_user_id", table_name="seeds")
    op.drop_table("seeds")
    op.drop_table("habits")
    op.drop_table("practices")
    op.drop_table("partners")
    op.drop_table("partner_groups")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")

