from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CompanyLead:
    name: str
    domain: str
    industry: str | None = None


@dataclass(frozen=True, slots=True)
class DecisionMaker:
    name: str
    title: str
    linkedin_url: str | None = None


@dataclass(frozen=True, slots=True)
class EmailLookupResult:
    email: str | None
    verified: bool


@dataclass(frozen=True, slots=True)
class EmailDraft:
    subject: str
    body: str


@dataclass(frozen=True, slots=True)
class EmailSendResult:
    message_id: str | None
