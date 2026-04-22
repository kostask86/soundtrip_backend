from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import TimePeriod
from app.schemas.ontology import TimePeriodCreate, TimePeriodUpdate


def create_time_period(db: Session, payload: TimePeriodCreate) -> TimePeriod:
    row = TimePeriod(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_time_period(db: Session, time_period_id: int) -> TimePeriod | None:
    return db.get(TimePeriod, time_period_id)


def list_time_periods(db: Session, limit: int = 50, offset: int = 0) -> list[TimePeriod]:
    stmt = select(TimePeriod).order_by(TimePeriod.id.asc()).offset(offset).limit(limit)
    return list(db.scalars(stmt))


def update_time_period(db: Session, row: TimePeriod, payload: TimePeriodUpdate) -> TimePeriod:
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete_time_period(db: Session, row: TimePeriod) -> None:
    db.delete(row)
    db.commit()
