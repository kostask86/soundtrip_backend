from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep
from app.schemas.ontology import EmotionCategoryRead, EmotionCategoryWithChildren, EmotionCreate, EmotionRead, EmotionUpdate
from app.services import emotions

router = APIRouter(prefix="/emotions", tags=["emotions"])


@router.post("", response_model=EmotionRead, status_code=status.HTTP_201_CREATED)
def create_emotion(db: SessionDep, payload: EmotionCreate) -> EmotionRead:
    try:
        row = emotions.create_emotion(db, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Emotion already exists or invalid category_id") from None
    return EmotionRead.model_validate(row)


@router.get("", response_model=list[EmotionCategoryWithChildren])
def list_emotions(
    db: SessionDep,
) -> list[EmotionCategoryWithChildren]:
    grouped = emotions.list_emotions_grouped_by_category(db)
    return [
        EmotionCategoryWithChildren(
            id=item["category"].id,
            key=item["category"].key,
            label=item["category"].label,
            children=[EmotionRead.model_validate(child) for child in item["children"]],
        )
        for item in grouped
    ]


@router.get("/categories", response_model=list[EmotionCategoryRead])
def list_emotion_categories(
    db: SessionDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[EmotionCategoryRead]:
    rows = emotions.list_emotion_categories(db, limit=limit, offset=offset)
    return [EmotionCategoryRead.model_validate(row) for row in rows]


@router.get("/{emotion_id}", response_model=EmotionRead)
def get_emotion(db: SessionDep, emotion_id: int) -> EmotionRead:
    row = emotions.get_emotion(db, emotion_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emotion not found")
    return EmotionRead.model_validate(row)


@router.put("/{emotion_id}", response_model=EmotionRead)
def update_emotion(db: SessionDep, emotion_id: int, payload: EmotionUpdate) -> EmotionRead:
    row = emotions.get_emotion(db, emotion_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emotion not found")
    try:
        updated = emotions.update_emotion(db, row, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Emotion already exists or invalid category_id") from None
    return EmotionRead.model_validate(updated)


@router.delete("/{emotion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_emotion(db: SessionDep, emotion_id: int) -> None:
    row = emotions.get_emotion(db, emotion_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emotion not found")
    emotions.delete_emotion(db, row)
