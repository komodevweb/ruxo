"""add last checkout tracking fields

Revision ID: add_last_checkout_tracking
Revises: 4b7e6c701840
Create Date: 2025-11-25

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_last_checkout_tracking'
down_revision = '4b7e6c701840'
branch_labels = None
depends_on = None


def upgrade():
    # Add last checkout tracking fields to user_profiles
    op.add_column('user_profiles', sa.Column('last_checkout_ip', sa.String(), nullable=True))
    op.add_column('user_profiles', sa.Column('last_checkout_user_agent', sa.String(), nullable=True))
    op.add_column('user_profiles', sa.Column('last_checkout_fbp', sa.String(), nullable=True))
    op.add_column('user_profiles', sa.Column('last_checkout_fbc', sa.String(), nullable=True))
    op.add_column('user_profiles', sa.Column('last_checkout_timestamp', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    # Remove last checkout tracking fields from user_profiles
    op.drop_column('user_profiles', 'last_checkout_timestamp')
    op.drop_column('user_profiles', 'last_checkout_fbc')
    op.drop_column('user_profiles', 'last_checkout_fbp')
    op.drop_column('user_profiles', 'last_checkout_user_agent')
    op.drop_column('user_profiles', 'last_checkout_ip')

