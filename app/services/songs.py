from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Song
from app.schemas.song import SongCreate, SongUpdate


def create_song(db: Session, payload: SongCreate) -> Song:
    song = Song(**payload.model_dump())
    db.add(song)
    db.commit()
    db.refresh(song)
    return song


def get_song(db: Session, song_id: int) -> Song | None:
    return db.get(Song, song_id)


def list_songs(db: Session, limit: int = 50, offset: int = 0) -> list[Song]:
    stmt = select(Song).order_by(Song.id.desc()).offset(offset).limit(limit)
    return list(db.scalars(stmt))


def update_song(db: Session, song: Song, payload: SongUpdate) -> Song:
    for field, value in payload.model_dump().items():
        setattr(song, field, value)
    db.commit()
    db.refresh(song)
    return song


def delete_song(db: Session, song: Song) -> None:
    db.delete(song)
    db.commit()
