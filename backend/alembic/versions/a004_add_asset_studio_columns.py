"""add template_instance_id and canvas_project_id to assets

Revision ID: a004_asset_fks
Revises: a003_fonts
Create Date: 2026-03-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a004_asset_fks'
down_revision: Union[str, Sequence[str], None] = 'a003_fonts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('template_instance_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('canvas_project_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_assets_template_instance_id',
            'template_instances',
            ['template_instance_id'],
            ['id'],
        )
        batch_op.create_foreign_key(
            'fk_assets_canvas_project_id',
            'canvas_projects',
            ['canvas_project_id'],
            ['id'],
        )


def downgrade() -> None:
    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.drop_constraint('fk_assets_canvas_project_id', type_='foreignkey')
        batch_op.drop_constraint('fk_assets_template_instance_id', type_='foreignkey')
        batch_op.drop_column('canvas_project_id')
        batch_op.drop_column('template_instance_id')
