"""add subscription fields

Revision ID: add_subscription_fields
Revises: rename_credits_column
Create Date: 2025-11-20 22:01:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'add_subscription_fields'
down_revision = 'rename_credits_column'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add plan_id foreign key to subscriptions
    op.add_column('subscriptions', sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_subscriptions_plan_id', 'subscriptions', 'plans', ['plan_id'], ['id'])
    
    # Add last_credit_reset column
    op.add_column('subscriptions', sa.Column('last_credit_reset', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove columns
    op.drop_column('subscriptions', 'last_credit_reset')
    op.drop_constraint('fk_subscriptions_plan_id', 'subscriptions', type_='foreignkey')
    op.drop_column('subscriptions', 'plan_id')

