"""module_9_platform_administration

Revision ID: 7f6692af0b54
Revises: e7abc1234567
Create Date: 2026-07-17 15:11:58.597192

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7f6692af0b54'
down_revision: Union[str, Sequence[str], None] = 'e7abc1234567'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('system_settings',
    sa.Column('key', sa.String(length=100), nullable=False),
    sa.Column('value', sa.Text(), nullable=False),
    sa.Column('description', sa.String(length=255), nullable=True),
    sa.Column('is_public', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_settings_key'), 'system_settings', ['key'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_system_settings_key'), table_name='system_settings')
    op.drop_table('system_settings')
    # ### end Alembic commands ###
