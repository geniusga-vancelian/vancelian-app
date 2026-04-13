"""remove_backtest_fk_admin_users_add_email

Revision ID: 929c08d54fcc
Revises: ee8235fabc5e
Create Date: 2026-01-08 18:25:01.025543

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '929c08d54fcc'
down_revision: Union[str, None] = 'ee8235fabc5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass


