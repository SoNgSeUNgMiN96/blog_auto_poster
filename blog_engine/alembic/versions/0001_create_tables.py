"""create initial tables

Revision ID: 0001_create_tables
Revises:
Create Date: 2026-02-22
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_create_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("raw_input", sa.JSON(), nullable=False),
        sa.Column("generated_content", sa.JSON(), nullable=True),
        sa.Column("rendered_html", sa.Text(), nullable=True),
        sa.Column("seo_title", sa.String(length=255), nullable=True),
        sa.Column("meta_description", sa.String(length=255), nullable=True),
        sa.Column("slug", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("wp_post_id", sa.Integer(), nullable=True),
        sa.Column("wp_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_posts_id", "posts", ["id"])
    op.create_unique_constraint("uq_posts_slug", "posts", ["slug"])

    op.create_table(
        "images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_url", sa.String(length=500), nullable=False),
        sa.Column("local_path", sa.String(length=500), nullable=False),
        sa.Column("wp_media_id", sa.Integer(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
    )
    op.create_index("ix_images_post_id", "images", ["post_id"])


def downgrade() -> None:
    op.drop_index("ix_images_post_id", table_name="images")
    op.drop_table("images")
    op.drop_constraint("uq_posts_slug", "posts", type_="unique")
    op.drop_index("ix_posts_id", table_name="posts")
    op.drop_table("posts")
