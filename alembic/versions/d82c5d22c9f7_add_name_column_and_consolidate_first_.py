"""Add name column and consolidate first_name last_name

Revision ID: d82c5d22c9f7
Revises: 78c10d7da504
Create Date: 2025-07-12 01:49:44.470817

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d82c5d22c9f7"
down_revision: str | Sequence[str] | None = "78c10d7da504"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add the new name column
    op.add_column("customers", sa.Column("name", sa.String(length=200), nullable=True))

    # Migrate existing data: combine first_name and last_name into name
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
        UPDATE customers
        SET name = CASE
            WHEN first_name IS NOT NULL AND last_name IS NOT NULL
                THEN CONCAT(first_name, ' ', last_name)
            WHEN first_name IS NOT NULL
                THEN first_name
            WHEN last_name IS NOT NULL
                THEN last_name
            ELSE NULL
        END
    """
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    # For downgrade, split name back into first_name and last_name (best effort)
    connection = op.get_bind()

    # Update first_name and last_name from name field (simple split on first space)
    connection.execute(
        sa.text(
            """
        UPDATE customers
        SET
            first_name = CASE
                WHEN name IS NOT NULL AND POSITION(' ' IN name) > 0
                    THEN SUBSTRING(name FROM 1 FOR POSITION(' ' IN name) - 1)
                WHEN name IS NOT NULL
                    THEN name
                ELSE first_name
            END,
            last_name = CASE
                WHEN name IS NOT NULL AND POSITION(' ' IN name) > 0
                    THEN SUBSTRING(name FROM POSITION(' ' IN name) + 1)
                ELSE last_name
            END
        WHERE name IS NOT NULL
    """
        )
    )

    # Remove the name column
    op.drop_column("customers", "name")
