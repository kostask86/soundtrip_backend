from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep
from app.schemas.ontology import TimePeriodCreate, TimePeriodRead, TimePeriodUpdate
from app.services import time_periods

router = APIRouter(prefix="/time-periods", tags=["time-periods"])


@router.post("", response_model=TimePeriodRead, status_code=status.HTTP_201_CREATED)
def create_time_period(db: SessionDep, payload: TimePeriodCreate) -> TimePeriodRead:
    try:
        row = time_periods.create_time_period(db, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Time period already exists") from None
    return TimePeriodRead.model_validate(row)


@router.get("", response_model=list[TimePeriodRead])
def list_time_periods(
    db: SessionDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[TimePeriodRead]:
    rows = time_periods.list_time_periods(db, limit=limit, offset=offset)
    return [TimePeriodRead.model_validate(row) for row in rows]


@router.get("/{time_period_id}", response_model=TimePeriodRead)
def get_time_period(db: SessionDep, time_period_id: int) -> TimePeriodRead:
    row = time_periods.get_time_period(db, time_period_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Time period not found")
    return TimePeriodRead.model_validate(row)


@router.put("/{time_period_id}", response_model=TimePeriodRead)
def update_time_period(db: SessionDep, time_period_id: int, payload: TimePeriodUpdate) -> TimePeriodRead:
    row = time_periods.get_time_period(db, time_period_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Time period not found")
    try:
        updated = time_periods.update_time_period(db, row, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Time period already exists") from None
    return TimePeriodRead.model_validate(updated)


@router.delete("/{time_period_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_time_period(db: SessionDep, time_period_id: int) -> None:
    row = time_periods.get_time_period(db, time_period_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Time period not found")
    time_periods.delete_time_period(db, row)
