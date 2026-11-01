"""Pages of substances by CAS number (/cas/<cas>/): the table the nightly build fills from the products
(app.catalog.cas_pages)."""

import sqlalchemy as sa

from alembic import op

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'cas_pages',
        sa.Column('cas', sa.String(20), primary_key=True),
        sa.Column('name', sa.String(300), nullable=False),
        sa.Column('synonyms', sa.JSON(), nullable=False),
        sa.Column('formula', sa.String(200)),
        sa.Column('molecular_weight', sa.String(40)),
        sa.Column('offers', sa.Integer(), nullable=False),
        sa.Column('brands', sa.JSON(), nullable=False),
        sa.Column('sections', sa.JSON(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table('cas_pages')
