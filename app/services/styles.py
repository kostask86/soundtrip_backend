from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Style
from app.schemas.ontology import StyleCreate, StyleUpdate


def create_style(db: Session, payload: StyleCreate) -> Style:
    row = Style(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_style(db: Session, style_id: int) -> Style | None:
    return db.get(Style, style_id)


def list_styles(db: Session, limit: int = 50, offset: int = 0) -> list[Style]:
    stmt = select(Style).order_by(Style.id.asc()).offset(offset).limit(limit)
    return list(db.scalars(stmt))


def update_style(db: Session, row: Style, payload: StyleUpdate) -> Style:
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete_style(db: Session, row: Style) -> None:
    db.delete(row)
    db.commit()
