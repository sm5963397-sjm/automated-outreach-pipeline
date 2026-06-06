from __future__ import annotations

import uuid

import typer
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.security import normalize_domain
from app.database.session import SessionLocal
from app.models.enums import CampaignStatus
from app.repositories import CampaignRepository
from app.services.factory import build_workflow

cli = typer.Typer(help="Automated Outreach Pipeline CLI")


def _print_summary(summary: dict[str, object]) -> None:
    typer.echo("")
    typer.echo(f"Companies Found: {summary.get('companies_found', 0)}")
    typer.echo(f"Contacts Found: {summary.get('contacts_found', 0)}")
    typer.echo(f"Verified Emails: {summary.get('verified_emails', 0)}")
    typer.echo(f"Emails Generated: {summary.get('emails_generated', 0)}")
    typer.echo("")


@cli.command()
def start(
    domain: str = typer.Argument(..., help="Source company domain, for example openai.com"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Approve sending after summary."),
) -> None:
    """Run discovery, show a summary, and optionally send approved emails."""
    settings = get_settings()
    setup_logging(settings)
    normalized_domain = normalize_domain(domain)

    try:
        with SessionLocal() as db:
            campaign_repo = CampaignRepository(db)
            campaign = campaign_repo.create(normalized_domain)
            db.commit()
            workflow = build_workflow(db)
            summary = workflow.prepare_campaign(campaign.id, normalized_domain)
            typer.echo(f"Campaign ID: {campaign.id}")
            _print_summary(summary.model_dump())

            if summary.verified_emails == 0:
                typer.echo("No verified emails were found. Nothing to send.")
                raise typer.Exit(code=0)
            proceed = yes or typer.confirm("Proceed?", default=False)
            if not proceed:
                typer.echo("Campaign saved with status AWAITING_APPROVAL.")
                raise typer.Exit(code=0)
            final_summary = workflow.send_campaign(campaign.id)
            typer.echo(f"Campaign completed: {CampaignStatus(campaign.status).value}")
            _print_summary(final_summary.model_dump())
    except SQLAlchemyError as exc:
        typer.echo(f"Database error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@cli.command()
def status(campaign_id: str) -> None:
    """Show campaign status and summary."""
    settings = get_settings()
    setup_logging(settings)
    with SessionLocal() as db:
        campaign = CampaignRepository(db).require(uuid.UUID(campaign_id))
        typer.echo(f"Campaign ID: {campaign.id}")
        typer.echo(f"Domain: {campaign.source_domain}")
        typer.echo(f"Status: {campaign.status}")
        _print_summary(campaign.summary or {})
        if campaign.error_message:
            typer.echo(f"Error: {campaign.error_message}")


if __name__ == "__main__":
    cli()
