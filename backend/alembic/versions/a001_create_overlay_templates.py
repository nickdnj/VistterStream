"""create overlay_templates and template_instances tables

Revision ID: a001_templates
Revises: 3a255adfea55
Create Date: 2026-03-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a001_templates'
down_revision: Union[str, Sequence[str], None] = '3a255adfea55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'overlay_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('config_schema', sa.Text(), nullable=False),
        sa.Column('default_config', sa.Text(), nullable=False),
        sa.Column('preview_path', sa.String(), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=True),
        sa.Column('is_bundled', sa.Boolean(), server_default='1', nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_overlay_templates_id'), 'overlay_templates', ['id'], unique=False)

    op.create_table(
        'template_instances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('config_values', sa.Text(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['template_id'], ['overlay_templates.id']),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_template_instances_id'), 'template_instances', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_template_instances_id'), table_name='template_instances')
    op.drop_table('template_instances')
    op.drop_index(op.f('ix_overlay_templates_id'), table_name='overlay_templates')
    op.drop_table('overlay_templates')
