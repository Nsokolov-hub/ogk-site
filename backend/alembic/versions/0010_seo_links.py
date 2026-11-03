"""SEO of 03.11.2026: the sort key of the CAS index (/cas/) and the IndexNow queue.

The sort key of existing pages is filled by the next build of the CAS pages (nightly, or `cli cas-pages`).
"""

import sqlalchemy as sa

from alembic import op

revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('cas_pages', sa.Column('sort_key', sa.String(300)))
    op.create_index(op.f('ix_cas_pages_sort_key'), 'cas_pages', ['sort_key'], unique=False)
    op.create_table(
        'indexnow_queue',
        sa.Column('path', sa.String(500), primary_key=True),
        sa.Column('queued_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_indexnow_queue_queued_at'), 'indexnow_queue', ['queued_at'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_indexnow_queue_queued_at'), table_name='indexnow_queue')
    op.drop_table('indexnow_queue')
    op.drop_index(op.f('ix_cas_pages_sort_key'), table_name='cas_pages')
    op.drop_column('cas_pages', 'sort_key')
