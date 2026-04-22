from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep
from app.schemas.ontology import InfluenceCreate, InfluenceRead, InfluenceUpdate
from app.services import influences

router = APIRouter(prefix="/influences", tags=["influences"])


@router.post("", response_model=InfluenceRead, status_code=status.HTTP_201_CREATED)
def create_influence(db: SessionDep, payload: InfluenceCreate) -> InfluenceRead:
    try:
        row = influences.create_influence(db, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Influence already exists or invalid category_id") from None
    return InfluenceRead.model_validate(row)


@router.get("", response_model=list[InfluenceRead])
def list_influences(
    db: SessionDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[InfluenceRead]:
    rows = influences.list_influences(db, limit=limit, offset=offset)
    return [InfluenceRead.model_validate(row) for row in rows]


@router.get("/{influence_id}", response_model=InfluenceRead)
def get_influence(db: SessionDep, influence_id: int) -> InfluenceRead:
    row = influences.get_influence(db, influence_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Influence not found")
    return InfluenceRead.model_validate(row)


@router.put("/{influence_id}", response_model=InfluenceRead)
def update_influence(db: SessionDep, influence_id: int, payload: InfluenceUpdate) -> InfluenceRead:
    row = influences.get_influence(db, influence_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Influence not found")
    try:
        updated = influences.update_influence(db, row, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Influence already exists or invalid category_id") from None
    return InfluenceRead.model_validate(updated)


@router.delete("/{influence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_influence(db: SessionDep, influence_id: int) -> None:
    row = influences.get_influence(db, influence_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Influence not found")
    influences.delete_influence(db, row)
