from fastapi import APIRouter, HTTPException

from app.agents.graph import run_travel_agent
from app.config import get_settings
from app.schemas import TravelPlanRequest, TravelPlanResponse
from app.storage.sqlite_store import SQLiteStore


router = APIRouter(prefix="/api/travel", tags=["travel"])


@router.post("/plan", response_model=TravelPlanResponse)
def create_travel_plan(payload: TravelPlanRequest) -> TravelPlanResponse:
    """Run the full travel decision workflow and return the generated report."""

    try:
        return run_travel_agent(payload, settings=get_settings())
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/report/{request_id}")
def get_report(request_id: str) -> dict:
    """Fetch a previously generated report by request id."""

    store = SQLiteStore(get_settings().database_path)
    store.initialize()
    report = store.get_report(request_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    return report.model_dump()


@router.get("/evidences/{request_id}")
def get_evidences(request_id: str) -> dict:
    """Fetch structured evidence behind a generated report."""

    store = SQLiteStore(get_settings().database_path)
    store.initialize()
    evidences = store.get_evidences(request_id)
    if not evidences:
        raise HTTPException(status_code=404, detail="evidences not found")
    return {
        "request_id": request_id,
        "evidences": [evidence.model_dump() for evidence in evidences],
    }

