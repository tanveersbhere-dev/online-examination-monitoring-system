"""module_7_ai_event_history

Revision ID: e7abc1234567
Revises: 6cbc60013015
Create Date: 2026-07-17 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e7abc1234567'
down_revision: Union[str, None] = '6cbc60013015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('ai_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('exam_session_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('source_module', sa.String(length=100), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['exam_session_id'], ['exam_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_events_exam_session_id'), 'ai_events', ['exam_session_id'], unique=False)
    op.create_index(op.f('ix_ai_events_event_type'), 'ai_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_ai_events_timestamp'), 'ai_events', ['timestamp'], unique=False)
    op.create_index(op.f('ix_ai_events_id'), 'ai_events', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ai_events_id'), table_name='ai_events')
    op.drop_index(op.f('ix_ai_events_timestamp'), table_name='ai_events')
    op.drop_index(op.f('ix_ai_events_event_type'), table_name='ai_events')
    op.drop_index(op.f('ix_ai_events_exam_session_id'), table_name='ai_events')
    op.drop_table('ai_events')
