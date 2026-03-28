"""create ShortForge tables (moments, clips, published_shorts, shortforge_config)

Revision ID: a005_shortforge
Revises: a004_asset_fks
Create Date: 2026-03-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a005_shortforge'
down_revision: Union[str, None] = 'a004_asset_fks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('__dummy__', recreate='never') as _:
        pass  # batch mode required for SQLite

    op.create_table(
        'moments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('camera_id', sa.Integer(), sa.ForeignKey('cameras.id'), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('trigger_type', sa.String(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('frame_path', sa.String()),
        sa.Column('status', sa.String(), server_default='detected'),
        sa.Column('error_message', sa.String()),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_moments_camera_id', 'moments', ['camera_id'])
    op.create_index('ix_moments_status', 'moments', ['status'])
    op.create_index('ix_moments_timestamp', 'moments', ['timestamp'])

    op.create_table(
        'clips',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('moment_id', sa.Integer(), sa.ForeignKey('moments.id'), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('duration_seconds', sa.Float()),
        sa.Column('width', sa.Integer()),
        sa.Column('height', sa.Integer()),
        sa.Column('rendered_path', sa.String()),
        sa.Column('headline', sa.String()),
        sa.Column('safe_to_publish', sa.Boolean(), server_default='1'),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_clips_moment_id', 'clips', ['moment_id'])

    op.create_table(
        'published_shorts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('clip_id', sa.Integer(), sa.ForeignKey('clips.id'), nullable=False),
        sa.Column('youtube_video_id', sa.String()),
        sa.Column('title', sa.String()),
        sa.Column('description', sa.Text()),
        sa.Column('tags', sa.String()),
        sa.Column('views', sa.Integer(), server_default='0'),
        sa.Column('published_at', sa.DateTime()),
        sa.Column('status', sa.String(), server_default='published'),
        sa.Column('error_message', sa.String()),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_published_shorts_clip_id', 'published_shorts', ['clip_id'])
    op.create_index('ix_published_shorts_status', 'published_shorts', ['status'])

    op.create_table(
        'shortforge_config',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('enabled', sa.Boolean(), server_default='0'),
        sa.Column('camera_id', sa.Integer(), sa.ForeignKey('cameras.id'), nullable=True),
        sa.Column('motion_threshold', sa.Float(), server_default='0.6'),
        sa.Column('brightness_threshold', sa.Float(), server_default='0.5'),
        sa.Column('activity_threshold', sa.Float(), server_default='0.7'),
        sa.Column('cooldown_seconds', sa.Integer(), server_default='120'),
        sa.Column('detector_interval_seconds', sa.Integer(), server_default='5'),
        sa.Column('max_shorts_per_day', sa.Integer(), server_default='6'),
        sa.Column('quiet_hours_start', sa.String(), server_default='22:00'),
        sa.Column('quiet_hours_end', sa.String(), server_default='06:00'),
        sa.Column('min_posting_interval_minutes', sa.Integer(), server_default='60'),
        sa.Column('default_tags', sa.String(), server_default=''),
        sa.Column('description_template', sa.Text(),
                  server_default='{{headline}} | {{location}} | {{conditions}}'),
        sa.Column('safety_gate_enabled', sa.Boolean(), server_default='1'),
        sa.Column('raw_clip_retention_days', sa.Integer(), server_default='7'),
        sa.Column('rendered_clip_retention_days', sa.Integer(), server_default='30'),
        sa.Column('snapshot_retention_days', sa.Integer(), server_default='3'),
        sa.Column('openai_api_key_enc', sa.String()),
        sa.Column('ai_model', sa.String(), server_default='gpt-4o-mini'),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )


def downgrade() -> None:
    op.drop_table('shortforge_config')
    op.drop_table('published_shorts')
    op.drop_table('clips')
    op.drop_table('moments')
