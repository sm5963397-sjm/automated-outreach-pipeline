"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-06 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_domain", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campaigns_source_domain", "campaigns", ["source_domain"])
    op.create_index("ix_campaigns_status", "campaigns", ["status"])

    op.create_table(
        "companies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("industry", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain"),
    )
    op.create_index("ix_companies_domain", "companies", ["domain"])

    op.create_table(
        "contacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("linkedin_url", sa.String(length=1024), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "name", "title", name="uq_contacts_company_name_title"),
        sa.UniqueConstraint("linkedin_url"),
    )
    op.create_index("ix_contacts_company_id", "contacts", ["company_id"])
    op.create_index("ix_contacts_email", "contacts", ["email"])

    op.create_table(
        "emails",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "contact_id", name="uq_emails_campaign_contact"),
    )
    op.create_index("ix_emails_campaign_id", "emails", ["campaign_id"])
    op.create_index("ix_emails_contact_id", "emails", ["contact_id"])
    op.create_index("ix_emails_provider_message_id", "emails", ["provider_message_id"])
    op.create_index("ix_emails_status", "emails", ["status"])


def downgrade() -> None:
    op.drop_index("ix_emails_status", table_name="emails")
    op.drop_index("ix_emails_provider_message_id", table_name="emails")
    op.drop_index("ix_emails_contact_id", table_name="emails")
    op.drop_index("ix_emails_campaign_id", table_name="emails")
    op.drop_table("emails")
    op.drop_index("ix_contacts_email", table_name="contacts")
    op.drop_index("ix_contacts_company_id", table_name="contacts")
    op.drop_table("contacts")
    op.drop_index("ix_companies_domain", table_name="companies")
    op.drop_table("companies")
    op.drop_index("ix_campaigns_status", table_name="campaigns")
    op.drop_index("ix_campaigns_source_domain", table_name="campaigns")
    op.drop_table("campaigns")
