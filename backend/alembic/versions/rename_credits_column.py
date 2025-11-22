"""rename credits_provided to credits_per_month

Revision ID: rename_credits_column
Revises: 38322ca50328
Create Date: 2025-11-20 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'rename_credits_column'
down_revision = '38322ca50328'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename column from credits_provided to credits_per_month
    op.alter_column('plans', 'credits_provided',
                    new_column_name='credits_per_month',
                    existing_type=sa.Integer(),
                    existing_nullable=False)


def downgrade() -> None:
    # Rename back to credits_provided
    op.alter_column('plans', 'credits_per_month',
                    new_column_name='credits_provided',
                    existing_type=sa.Integer(),
                    existing_nullable=False)

