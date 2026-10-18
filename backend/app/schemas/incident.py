from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


IncidentDomain = Literal[
    "devops",
    "ai_engineering",
    "postgresql",
    "enterprise_it",
    "security",
]

IncidentSeverity = Literal[
    "low",
    "medium",
    "high",
    "critical",
]


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)

    description: str = Field(min_length=10)

    domain: IncidentDomain

    severity: IncidentSeverity = "medium"


class IncidentResponse(BaseModel):
    id: int

    title: str

    description: str

    domain: str

    severity: str

    status: str

    investigation_report: dict[str, Any] | None = None

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)