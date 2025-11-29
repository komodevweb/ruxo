"""add trial fields to plans

Revision ID: add_trial_fields_to_plans
Revises: add_last_checkout_tracking
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_trial_fields_to_plans'
down_revision = 'add_last_checkout_tracking'
branch_labels = None
depends_on = None


def upgrade():
    # Add trial period configuration fields to plans table
    op.add_column('plans', sa.Column('trial_days', sa.Integer(), nullable=False, server_default='3'))
    op.add_column('plans', sa.Column('trial_amount_cents', sa.Integer(), nullable=False, server_default='100'))
    op.add_column('plans', sa.Column('trial_credits', sa.Integer(), nullable=False, server_default='60'))


def downgrade():
    # Remove trial fields from plans table
    op.drop_column('plans', 'trial_credits')
    op.drop_column('plans', 'trial_amount_cents')
    op.drop_column('plans', 'trial_days')

