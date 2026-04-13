"""merge_feature_and_backtest_heads

Revision ID: f01ee54920d6
Revises: 009, 929c08d54fcc, ff1234abcd56
Create Date: 2026-01-12 17:51:30.174371

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f01ee54920d6'
down_revision: Union[str, None] = ('009', '929c08d54fcc', 'ff1234abcd56')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass


