from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep
from app.schemas.ontology import GeographyCreate, GeographyRead, GeographyUpdate
from app.services import geographies

router = APIRouter(prefix="/geographies", tags=["geographies"])


@router.post("", response_model=GeographyRead, status_code=status.HTTP_201_CREATED)
def create_geography(db: SessionDep, payload: GeographyCreate) -> GeographyRead:
    try:
        row = geographies.create_geography(db, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Geography already exists") from None
    return GeographyRead.model_validate(row)


@router.get("", response_model=list[GeographyRead])
def list_geographies(
    db: SessionDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[GeographyRead]:
    rows = geographies.list_geographies(db, limit=limit, offset=offset)
    return [GeographyRead.model_validate(row) for row in rows]


@router.get("/{geography_id}", response_model=GeographyRead)
def get_geography(db: SessionDep, geography_id: int) -> GeographyRead:
    row = geographies.get_geography(db, geography_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Geography not found")
    return GeographyRead.model_validate(row)


@router.put("/{geography_id}", response_model=GeographyRead)
def update_geography(db: SessionDep, geography_id: int, payload: GeographyUpdate) -> GeographyRead:
    row = geographies.get_geography(db, geography_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Geography not found")
    try:
        updated = geographies.update_geography(db, row, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Geography already exists") from None
    return GeographyRead.model_validate(updated)


@router.delete("/{geography_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_geography(db: SessionDep, geography_id: int) -> None:
    row = geographies.get_geography(db, geography_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Geography not found")
    geographies.delete_geography(db, row)
