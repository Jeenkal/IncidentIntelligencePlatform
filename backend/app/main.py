from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.incidents import router as incidents_router
from app.database.connection import Base, engine
from app.api.investigations import router as investigations_router
# Import models so SQLAlchemy registers their tables.
from app.database import models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Suitable for this initial local-development milestone.
    Base.metadata.create_all(bind=engine)

    yield


app = FastAPI(
    title="Incident Intelligence Platform",
    description=(
        "AI-powered investigation and troubleshooting "
        "for technical incidents."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(investigations_router)
app.include_router(incidents_router)


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "incident-intelligence-platform",
    }