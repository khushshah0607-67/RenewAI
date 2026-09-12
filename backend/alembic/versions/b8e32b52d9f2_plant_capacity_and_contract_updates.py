"""plant capacity and backend contract updates

Revision ID: b8e32b52d9f2
Revises: 9baf4d80ea13
Create Date: 2026-09-12 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by atexit.
revision = "b8e32b52d9f2"
down_revision = "9baf4d80ea13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("plants", sa.Column("installed_capacity_mw", sa.Float(), nullable=True))
    op.add_column("plants", sa.Column("export_limit_mw", sa.Float(), nullable=True))

    op.execute(
        "UPDATE plants SET installed_capacity_mw = capacity_mw WHERE installed_capacity_mw IS NULL"
    )

    op.alter_column("plants", "installed_capacity_mw", nullable=False)
    op.create_check_constraint(
        "ck_plants_installed_capacity_positive",
        "plants",
        "installed_capacity_mw > 0",
    )
    op.create_check_constraint(
        "ck_plants_export_limit_positive",
        "plants",
        "export_limit_mw IS NULL OR export_limit_mw > 0",
    )
    op.create_check_constraint(
        "ck_plants_export_limit_within_capacity",
        "plants",
        "export_limit_mw IS NULL OR export_limit_mw <= installed_capacity_mw",
    )

    op.create_unique_constraint("uq_historical_generation_plant_timestamp", "historical_generation", ["plant_id", "timestamp"])
    op.create_unique_constraint("uq_weather_data_plant_timestamp", "weather_data", ["plant_id", "timestamp"])
    op.create_unique_constraint("uq_forecasts_plant_timestamp", "forecasts", ["plant_id", "forecast_timestamp"])


def downgrade() -> None:
    op.drop_constraint("uq_forecasts_plant_timestamp", "forecasts", type_="unique")
    op.drop_constraint("uq_weather_data_plant_timestamp", "weather_data", type_="unique")
    op.drop_constraint("uq_historical_generation_plant_timestamp", "historical_generation", type_="unique")

    op.drop_constraint("ck_plants_export_limit_within_capacity", "plants", type_="check")
    op.drop_constraint("ck_plants_export_limit_positive", "plants", type_="check")
    op.drop_constraint("ck_plants_installed_capacity_positive", "plants", type_="check")

    op.drop_column("plants", "export_limit_mw")
    op.drop_column("plants", "installed_capacity_mw")
