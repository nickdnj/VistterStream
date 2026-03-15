"""create fonts table

Revision ID: a003_fonts
Revises: a002_canvas
Create Date: 2026-03-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a003_fonts'
down_revision: Union[str, Sequence[str], None] = 'a002_canvas'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'fonts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('family', sa.String(), nullable=False),
        sa.Column('weight', sa.String(), server_default='400', nullable=True),
        sa.Column('style', sa.String(), server_default='normal', nullable=True),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_fonts_id'), 'fonts', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_fonts_id'), table_name='fonts')
    op.drop_table('fonts')
