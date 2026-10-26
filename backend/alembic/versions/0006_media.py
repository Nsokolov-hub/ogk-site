"""2D structures from SMILES: the SMILES of the last drawing and the queue of cards to draw"""

import sqlalchemy as sa

from alembic import op

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('products') as batch:
        batch.add_column(sa.Column('structure_smiles', sa.Text(), nullable=True))
    op.create_index('ix_products_structure_pending', 'products', ['id'], unique=False,
                    postgresql_where=sa.text('structure_smiles IS DISTINCT FROM smiles'),
                    sqlite_where=sa.text('structure_smiles IS NOT smiles'))


def downgrade():
    op.drop_index('ix_products_structure_pending', table_name='products')
    with op.batch_alter_table('products') as batch:
        batch.drop_column('structure_smiles')
