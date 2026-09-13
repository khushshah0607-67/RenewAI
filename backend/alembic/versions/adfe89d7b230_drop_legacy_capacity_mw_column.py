"""drop legacy capacity_mw column after canonical installed_capacity_mw migration

Revision ID: adfe89d7b230
Revises: b8e32b52d9f2
Create Date: 2026-09-13 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by atexit.
revision = "adfe89d7b230"
down_revision = "b8e32b52d9f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "plants" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("plants")}
    if "capacity_mw" not in columns and "installed_capacity_mw" in columns:
        return

    if "installed_capacity_mw" in columns and "capacity_mw" in columns:
        op.execute(
            sa.text(
                "UPDATE plants SET installed_capacity_mw = capacity_mw "
                "WHERE installed_capacity_mw IS NULL AND capacity_mw IS NOT NULL"
            )
        )
        op.execute(
            sa.text(
                "UPDATE plants SET capacity_mw = installed_capacity_mw "
                "WHERE capacity_mw IS NULL AND installed_capacity_mw IS NOT NULL"
            )
        )

    if "capacity_mw" in columns:
        op.drop_column("plants", "capacity_mw")

    # Keep the canonical column as the single source of truth.
    if "installed_capacity_mw" in columns:
        op.execute(
            sa.text(
                "UPDATE plants SET installed_capacity_mw = installed_capacity_mw "
                "WHERE installed_capacity_mw IS NOT NULL"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "plants" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("plants")}
    if "capacity_mw" not in columns and "installed_capacity_mw" in columns:
        op.add_column("plants", sa.Column("capacity_mw", sa.Float(), nullable=True))
        op.execute(
            sa.text(
                "UPDATE plants SET capacity_mw = installed_capacity_mw "
                "WHERE capacity_mw IS NULL AND installed_capacity_mw IS NOT NULL"
            )
        )
