from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Influence, InfluenceCategory
from app.schemas.ontology import InfluenceCreate, InfluenceUpdate


def create_influence(db: Session, payload: InfluenceCreate) -> Influence:
    row = Influence(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_influence(db: Session, influence_id: int) -> Influence | None:
    return db.get(Influence, influence_id)


def list_influences(db: Session, limit: int = 50, offset: int = 0) -> list[Influence]:
    stmt = select(Influence).order_by(Influence.id.asc()).offset(offset).limit(limit)
    return list(db.scalars(stmt))


def list_influence_categories(db: Session, limit: int = 100, offset: int = 0) -> list[InfluenceCategory]:
    stmt = select(InfluenceCategory).order_by(InfluenceCategory.id.asc()).offset(offset).limit(limit)
    return list(db.scalars(stmt))


def list_influences_grouped_by_category(db: Session) -> list[dict]:
    categories = list(db.scalars(select(InfluenceCategory).order_by(InfluenceCategory.id.asc())))
    influences = list(db.scalars(select(Influence).order_by(Influence.id.asc())))
    grouped: dict[int, list[Influence]] = {}
    for row in influences:
        grouped.setdefault(row.category_id, []).append(row)
    return [{"category": category, "children": grouped.get(category.id, [])} for category in categories]


def update_influence(db: Session, row: Influence, payload: InfluenceUpdate) -> Influence:
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete_influence(db: Session, row: Influence) -> None:
    db.delete(row)
    db.commit()
