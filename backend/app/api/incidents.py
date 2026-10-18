from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Incident, IncidentEvent
from app.schemas.incident import IncidentCreate, IncidentResponse

router = APIRouter(
    prefix="/incidents",
    tags=["Incidents"],
)


@router.post(
    "",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_incident(
    request: IncidentCreate,
    db: Session = Depends(get_db),
):
    incident = Incident(
        title=request.title,
        description=request.description,
        domain=request.domain,
        severity=request.severity,
        status="open",
    )

    db.add(incident)
    db.flush()

    event = IncidentEvent(
        incident_id=incident.id,
        event_type="incident_created",
        message="Incident created and awaiting investigation.",
    )

    db.add(event)
    db.commit()
    db.refresh(incident)

    return incident


@router.get("", response_model=list[IncidentResponse])
def list_incidents(
    db: Session = Depends(get_db),
):
    return (
        db.query(Incident)
        .order_by(Incident.created_at.desc())
        .all()
    )


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
):
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

    return incident