"""create canvas_projects table

Revision ID: a002_canvas
Revises: a001_templates
Create Date: 2026-03-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a002_canvas'
down_revision: Union[str, Sequence[str], None] = 'a001_templates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'canvas_projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('canvas_json', sa.Text(), nullable=False),
        sa.Column('thumbnail_path', sa.String(), nullable=True),
        sa.Column('width', sa.Integer(), server_default='1920', nullable=True),
        sa.Column('height', sa.Integer(), server_default='1080', nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_canvas_projects_id'), 'canvas_projects', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_canvas_projects_id'), table_name='canvas_projects')
    op.drop_table('canvas_projects')
