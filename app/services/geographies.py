from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Geography
from app.schemas.ontology import GeographyCreate, GeographyUpdate


def create_geography(db: Session, payload: GeographyCreate) -> Geography:
    row = Geography(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_geography(db: Session, geography_id: int) -> Geography | None:
    return db.get(Geography, geography_id)


def list_geographies(db: Session, limit: int = 50, offset: int = 0) -> list[Geography]:
    stmt = select(Geography).order_by(Geography.id.asc()).offset(offset).limit(limit)
    return list(db.scalars(stmt))


def update_geography(db: Session, row: Geography, payload: GeographyUpdate) -> Geography:
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete_geography(db: Session, row: Geography) -> None:
    db.delete(row)
    db.commit()
