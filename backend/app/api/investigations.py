from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Incident, IncidentEvent
from app.agents.graph import investigation_graph

router = APIRouter(
    prefix="/incidents",
    tags=["Investigations"],
)


@router.post("/{incident_id}/investigate")
def investigate_incident(
    incident_id: int,
    db: Session = Depends(get_db),
):
    # 1. Find the incident
    incident = (
        db.query(Incident)
        .filter(Incident.id == incident_id)
        .first()
    )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found.",
        )

    # 2. Mark investigation as started
    incident.status = "investigating"

    db.add(
        IncidentEvent(
            incident_id=incident.id,
            event_type="investigation_started",
            message="AI investigation started.",
        )
    )

    db.commit()

    try:
        # 3. Execute the LangGraph investigation workflow
        result = investigation_graph.invoke(
            {
                "incident_id": incident.id,
                "title": incident.title,
                "description": incident.description,
                "domain": incident.domain,
                "current_query": (
                    f"{incident.title}\n{incident.description}"
                ),
                "retry_count": 0,
                "max_retries": 1,
                "evidence": [],
                "hypotheses": [],
                "verification": {},
                "report": {},
                "status": "investigating",
                "error": None,
            },
            config={"recursion_limit": 20},
        )

        # 4. Validate the investigation result
        report = result.get("report")

        if not isinstance(report, dict) or not report:
            raise RuntimeError(
                "The investigation workflow returned no valid report."
            )

        # 5. Determine the final workflow status
        verification = result.get("verification") or {}

        if verification.get("sufficient_evidence") is True:
            final_status = "completed"
        else:
            final_status = "insufficient_evidence"

        # 6. Save the report
        incident.investigation_report = report
        incident.status = final_status

        db.add(
            IncidentEvent(
                incident_id=incident.id,
                event_type="investigation_completed",
                message=(
                    "Investigation workflow finished with status: "
                    f"{final_status}"
                ),
            )
        )

        db.commit()

        return {
            "incident_id": incident.id,
            "status": final_status,
            "report": report,
            "retry_count": result.get("retry_count", 0),
        }

    except Exception as exc:
        db.rollback()

        # 7. Record the failure
        failed_incident = (
            db.query(Incident)
            .filter(Incident.id == incident_id)
            .first()
        )

        if failed_incident:
            failed_incident.status = "investigation_failed"

            db.add(
                IncidentEvent(
                    incident_id=incident_id,
                    event_type="investigation_failed",
                    message=(
                        "Investigation failed. "
                        "Check the backend logs."
                    ),
                )
            )

            db.commit()

        # Log the underlying exception in the backend terminal.
        print(
            f"[Investigation Error] Incident {incident_id}: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail="Investigation failed. Check the backend logs.",
        ) from exc