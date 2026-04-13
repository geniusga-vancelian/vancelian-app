"""merge_heads

Revision ID: 012
Revises: 011, h3456789012c
Create Date: 2026-01-21

Fusionne les têtes 011 (chatbot) et h3456789012c (bundle_id backtest) pour avoir un seul head.
"""
from typing import Sequence, Union

revision = "012"
down_revision: Union[str, tuple] = ("011", "h3456789012c")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
