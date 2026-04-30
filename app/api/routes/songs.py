from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep
from app.schemas.song import SongCreate, SongRead, SongUpdate
from app.services import songs

router = APIRouter(prefix="/songs", tags=["songs"])


@router.post("", response_model=SongRead, status_code=status.HTTP_201_CREATED)
def create_song(db: SessionDep, payload: SongCreate) -> SongRead:
    song = songs.create_song(db, payload)
    return SongRead.model_validate(song)


@router.get("", response_model=list[SongRead])
def list_songs(
    db: SessionDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[SongRead]:
    rows = songs.list_songs(db, limit=limit, offset=offset)
    return [SongRead.model_validate(row) for row in rows]


@router.get("/{song_id}", response_model=SongRead)
def get_song(db: SessionDep, song_id: int) -> SongRead:
    song = songs.get_song(db, song_id)
    if song is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    return SongRead.model_validate(song)


@router.put("/{song_id}", response_model=SongRead)
def update_song(db: SessionDep, song_id: int, payload: SongUpdate) -> SongRead:
    song = songs.get_song(db, song_id)
    if song is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    try:
        updated = songs.update_song(db, song, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid song update") from None
    return SongRead.model_validate(updated)


@router.delete("/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_song(db: SessionDep, song_id: int) -> None:
    song = songs.get_song(db, song_id)
    if song is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    songs.delete_song(db, song)


@router.post("/{song_id}/metadata/apply", response_model=SongRead)
def apply_song_metadata(db: SessionDep, song_id: int) -> SongRead:
    song = songs.get_song(db, song_id)
    if song is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    updated = songs.apply_spotify_metadata(db, song)
    return SongRead.model_validate(updated)
