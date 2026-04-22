from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep
from app.schemas.ontology import StyleCreate, StyleRead, StyleUpdate
from app.services import styles

router = APIRouter(prefix="/styles", tags=["styles"])


@router.post("", response_model=StyleRead, status_code=status.HTTP_201_CREATED)
def create_style(db: SessionDep, payload: StyleCreate) -> StyleRead:
    try:
        row = styles.create_style(db, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Style already exists or invalid parent_id") from None
    return StyleRead.model_validate(row)


@router.get("", response_model=list[StyleRead])
def list_styles(
    db: SessionDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[StyleRead]:
    rows = styles.list_styles(db, limit=limit, offset=offset)
    return [StyleRead.model_validate(row) for row in rows]


@router.get("/{style_id}", response_model=StyleRead)
def get_style(db: SessionDep, style_id: int) -> StyleRead:
    row = styles.get_style(db, style_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Style not found")
    return StyleRead.model_validate(row)


@router.put("/{style_id}", response_model=StyleRead)
def update_style(db: SessionDep, style_id: int, payload: StyleUpdate) -> StyleRead:
    row = styles.get_style(db, style_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Style not found")
    try:
        updated = styles.update_style(db, row, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Style already exists or invalid parent_id") from None
    return StyleRead.model_validate(updated)


@router.delete("/{style_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_style(db: SessionDep, style_id: int) -> None:
    row = styles.get_style(db, style_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Style not found")
    styles.delete_style(db, row)
