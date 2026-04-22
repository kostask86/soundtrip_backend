from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep
from app.schemas.ontology import InfluenceCategoryRead, InfluenceCategoryWithChildren, InfluenceCreate, InfluenceRead, InfluenceUpdate
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


@router.get("", response_model=list[InfluenceCategoryWithChildren])
def list_influences(
    db: SessionDep,
) -> list[InfluenceCategoryWithChildren]:
    grouped = influences.list_influences_grouped_by_category(db)
    return [
        InfluenceCategoryWithChildren(
            id=item["category"].id,
            key=item["category"].key,
            label=item["category"].label,
            children=[InfluenceRead.model_validate(child) for child in item["children"]],
        )
        for item in grouped
    ]


@router.get("/categories", response_model=list[InfluenceCategoryRead])
def list_influence_categories(
    db: SessionDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[InfluenceCategoryRead]:
    rows = influences.list_influence_categories(db, limit=limit, offset=offset)
    return [InfluenceCategoryRead.model_validate(row) for row in rows]


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
