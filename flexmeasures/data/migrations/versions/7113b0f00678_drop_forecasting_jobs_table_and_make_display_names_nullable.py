"""drop forecasting jobs table and make display names nullable

Revision ID: 7113b0f00678
Revises: ac2613fffc74
Create Date: 2020-06-04 11:29:46.507095

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "7113b0f00678"
down_revision = "ac2613fffc74"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("forecasting_job")
    op.alter_column(
        "asset_type",
        "display_name",
        existing_type=sa.VARCHAR(length=80),
        nullable=True,
        existing_server_default=sa.text("''::character varying"),
    )
    op.alter_column(
        "market",
        "display_name",
        existing_type=sa.VARCHAR(length=80),
        nullable=True,
        existing_server_default=sa.text("''::character varying"),
    )
    op.alter_column(
        "market_type",
        "display_name",
        existing_type=sa.VARCHAR(length=80),
        nullable=True,
        existing_server_default=sa.text("''::character varying"),
    )
    op.alter_column(
        "weather_sensor_type",
        "display_name",
        existing_type=sa.VARCHAR(length=80),
        nullable=True,
        existing_server_default=sa.text("''::character varying"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "weather_sensor_type",
        "display_name",
        existing_type=sa.VARCHAR(length=80),
        nullable=False,
        existing_server_default=sa.text("''::character varying"),
    )
    op.alter_column(
        "market_type",
        "display_name",
        existing_type=sa.VARCHAR(length=80),
        nullable=False,
        existing_server_default=sa.text("''::character varying"),
    )
    op.alter_column(
        "market",
        "display_name",
        existing_type=sa.VARCHAR(length=80),
        nullable=False,
        existing_server_default=sa.text("''::character varying"),
    )
    op.alter_column(
        "asset_type",
        "display_name",
        existing_type=sa.VARCHAR(length=80),
        nullable=False,
        existing_server_default=sa.text("''::character varying"),
    )
    op.create_table(
        "forecasting_job",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column(
            "timed_value_type",
            sa.VARCHAR(length=30),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("asset_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "start",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "end",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "horizon", postgresql.INTERVAL(), autoincrement=False, nullable=False
        ),
        sa.Column(
            "in_progress_since",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id", name="forecasting_job_pkey"),
    )
    # ### end Alembic commands ###
