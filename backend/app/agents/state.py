from typing import Any, TypedDict


class InvestigationState(TypedDict, total=False):
    incident_id: int
    title: str
    description: str
    domain: str

    current_query: str
    retry_count: int
    max_retries: int

    evidence: list[dict[str, Any]]
    hypotheses: list[dict[str, Any]]

    verification: dict[str, Any]
    report: dict[str, Any]

    status: str
    error: str