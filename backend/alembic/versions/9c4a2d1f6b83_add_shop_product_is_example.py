"""Add an example flag to shop products.

Revision ID: 9c4a2d1f6b83
Revises: 447ca9595700
Create Date: 2026-10-30

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c4a2d1f6b83"
down_revision: str | Sequence[str] | None = "447ca9595700"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "shop_products",
        sa.Column(
            "is_example",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("shop_products", "is_example")
