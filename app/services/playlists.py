from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.tables import Playlist, PlaylistSong, Song
from app.schemas.playlist import PlaylistCreate, PlaylistSong as PlaylistSongSchema, PlaylistStoredRead, PlaylistUpdate


def _song_schema_to_song_row(song: PlaylistSongSchema) -> Song:
    return Song(
        title=song.title,
        artist=song.artist,
        notes=json.dumps(song.model_dump()),
    )


def _extract_playlist_songs(db: Session, playlist_id: int, fallback_songs_json: str) -> list[dict]:
    links = list(
        db.scalars(
            select(PlaylistSong)
            .where(PlaylistSong.playlist_id == playlist_id)
            .order_by(PlaylistSong.position.asc())
        )
    )
    if not links:
        return json.loads(fallback_songs_json)
    songs: list[dict] = []
    for link in links:
        row = db.get(Song, link.song_id)
        if row is None:
            continue
        if row.notes:
            try:
                songs.append(json.loads(row.notes))
                continue
            except json.JSONDecodeError:
                pass
        songs.append(
            {
                "title": row.title,
                "artist": row.artist,
                "styles": [],
                "emotions": [],
                "time": {"id": "", "label": ""},
                "geography": {"primary": {"id": "", "label": ""}, "secondary": []},
                "influences": [],
            }
        )
    return songs


def _to_read_model(row: Playlist) -> PlaylistStoredRead:
    return PlaylistStoredRead(
        id=row.id,
        title=row.title,
        user_prompt=row.user_prompt,
        songs=[],
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def create_playlist(db: Session, payload: PlaylistCreate) -> PlaylistStoredRead:
    now = datetime.now(timezone.utc)
    row = Playlist(
        title=payload.title,
        user_prompt=payload.user_prompt,
        songs_json=json.dumps([song.model_dump() for song in payload.songs]),
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    for idx, song in enumerate(payload.songs):
        song_row = _song_schema_to_song_row(song)
        db.add(song_row)
        db.flush()
        db.add(PlaylistSong(playlist_id=row.id, song_id=song_row.id, position=idx))
    db.commit()
    db.refresh(row)
    result = _to_read_model(row)
    result.songs = _extract_playlist_songs(db, row.id, row.songs_json)
    return result


def get_playlist(db: Session, playlist_id: int) -> PlaylistStoredRead | None:
    row = db.get(Playlist, playlist_id)
    if row is None:
        return None
    result = _to_read_model(row)
    result.songs = _extract_playlist_songs(db, row.id, row.songs_json)
    return result


def list_playlists(db: Session, limit: int = 50, offset: int = 0) -> list[PlaylistStoredRead]:
    stmt = select(Playlist).order_by(Playlist.created_at.desc()).offset(offset).limit(limit)
    rows = list(db.scalars(stmt))
    result: list[PlaylistStoredRead] = []
    for row in rows:
        item = _to_read_model(row)
        item.songs = _extract_playlist_songs(db, row.id, row.songs_json)
        result.append(item)
    return result


def update_playlist(db: Session, playlist_id: int, payload: PlaylistUpdate) -> PlaylistStoredRead | None:
    row = db.get(Playlist, playlist_id)
    if row is None:
        return None
    row.title = payload.title
    row.user_prompt = payload.user_prompt
    row.songs_json = json.dumps([song.model_dump() for song in payload.songs])
    row.updated_at = datetime.now(timezone.utc)
    db.execute(delete(PlaylistSong).where(PlaylistSong.playlist_id == row.id))
    db.flush()
    for idx, song in enumerate(payload.songs):
        song_row = _song_schema_to_song_row(song)
        db.add(song_row)
        db.flush()
        db.add(PlaylistSong(playlist_id=row.id, song_id=song_row.id, position=idx))
    db.commit()
    db.refresh(row)
    result = _to_read_model(row)
    result.songs = _extract_playlist_songs(db, row.id, row.songs_json)
    return result


def delete_playlist(db: Session, playlist_id: int) -> bool:
    row = db.get(Playlist, playlist_id)
    if row is None:
        return False
    db.execute(delete(PlaylistSong).where(PlaylistSong.playlist_id == row.id))
    db.delete(row)
    db.commit()
    return True
