from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f91c5163dae0"
down_revision = "2da6d299b76e"  # например: "3a1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("locations", sa.Column("name", sa.String(length=120), nullable=True))
    op.add_column("locations", sa.Column("address", sa.String(length=255), nullable=True))
    op.add_column("locations", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("locations", sa.Column("longitude", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("locations", "longitude")
    op.drop_column("locations", "latitude")
    op.drop_column("locations", "address")
    op.drop_column("locations", "name")