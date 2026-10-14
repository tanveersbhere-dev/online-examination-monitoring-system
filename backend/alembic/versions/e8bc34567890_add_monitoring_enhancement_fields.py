"""add_monitoring_enhancement_fields

Revision ID: e8bc34567890
Revises: d7b0af0818db
Create Date: 2026-08-15 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8bc34567890'
down_revision: Union[str, Sequence[str], None] = 'd7b0af0818db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Violations table enhancements
    op.add_column('violations', sa.Column('duration_seconds', sa.Float(), server_default='0.0', nullable=False))
    op.add_column('violations', sa.Column('confidence', sa.Float(), nullable=True))
    op.add_column('violations', sa.Column('external_violation_id', sa.String(length=100), nullable=True))
    op.add_column('violations', sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_violations_exam_session_status', 'violations', ['exam_session_id', 'status'], unique=False)
    op.create_index('ix_violations_external_id', 'violations', ['external_violation_id'], unique=False)

    # Evidence table enhancements
    op.add_column('evidence', sa.Column('is_primary', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('evidence', sa.Column('replay_clip_path', sa.String(length=512), nullable=True))
    op.create_index('ix_evidence_violation_primary', 'evidence', ['violation_id', 'is_primary'], unique=False)

    # AI Sessions table enhancements
    op.add_column('ai_sessions', sa.Column('monitoring_status', sa.String(length=50), server_default='ACTIVE', nullable=False))
    op.add_column('ai_sessions', sa.Column('frames_processed', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('ai_sessions', 'frames_processed')
    op.drop_column('ai_sessions', 'monitoring_status')

    op.drop_index('ix_evidence_violation_primary', table_name='evidence')
    op.drop_column('evidence', 'replay_clip_path')
    op.drop_column('evidence', 'is_primary')

    op.drop_index('ix_violations_external_id', table_name='violations')
    op.drop_index('ix_violations_exam_session_status', table_name='violations')
    op.drop_column('violations', 'resolved_at')
    op.drop_column('violations', 'external_violation_id')
    op.drop_column('violations', 'confidence')
    op.drop_column('violations', 'duration_seconds')
