from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Emotion, EmotionCategory
from app.schemas.ontology import EmotionCreate, EmotionUpdate


def create_emotion(db: Session, payload: EmotionCreate) -> Emotion:
    row = Emotion(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_emotion(db: Session, emotion_id: int) -> Emotion | None:
    return db.get(Emotion, emotion_id)


def list_emotions(db: Session, limit: int = 50, offset: int = 0) -> list[Emotion]:
    stmt = select(Emotion).order_by(Emotion.id.asc()).offset(offset).limit(limit)
    return list(db.scalars(stmt))


def list_emotion_categories(db: Session, limit: int = 100, offset: int = 0) -> list[EmotionCategory]:
    stmt = select(EmotionCategory).order_by(EmotionCategory.id.asc()).offset(offset).limit(limit)
    return list(db.scalars(stmt))


def list_emotions_grouped_by_category(db: Session) -> list[dict]:
    categories = list(db.scalars(select(EmotionCategory).order_by(EmotionCategory.id.asc())))
    emotions = list(db.scalars(select(Emotion).order_by(Emotion.id.asc())))
    grouped: dict[int, list[Emotion]] = {}
    for row in emotions:
        grouped.setdefault(row.category_id, []).append(row)
    return [{"category": category, "children": grouped.get(category.id, [])} for category in categories]


def update_emotion(db: Session, row: Emotion, payload: EmotionUpdate) -> Emotion:
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete_emotion(db: Session, row: Emotion) -> None:
    db.delete(row)
    db.commit()
