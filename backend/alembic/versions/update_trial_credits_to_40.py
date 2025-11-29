"""update trial credits to 40

Revision ID: update_trial_credits_to_40
Revises: add_trial_fields_to_plans
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'update_trial_credits_to_40'
down_revision = 'add_trial_fields_to_plans'
branch_labels = None
depends_on = None


def upgrade():
    # Update all plans to have 40 trial credits (was 60)
    op.execute("UPDATE plans SET trial_credits = 40 WHERE trial_credits != 40 OR trial_credits IS NULL")


def downgrade():
    # Revert to 60 credits (if needed)
    op.execute("UPDATE plans SET trial_credits = 60 WHERE trial_credits = 40")

