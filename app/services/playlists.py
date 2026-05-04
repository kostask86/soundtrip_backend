from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.tables import (
    Emotion,
    Geography,
    Influence,
    Playlist,
    PlaylistSong,
    Song,
    SongEmotion,
    SongInfluence,
    SongSecondaryGeography,
    SongStyle,
    Style,
    TimePeriod,
)
from app.schemas.playlist import PlaylistCreate, PlaylistSong as PlaylistSongSchema, PlaylistStoredRead, PlaylistUpdate


def _song_schema_to_song_row(
    song: PlaylistSongSchema,
    time_period_by_key: dict[str, TimePeriod],
    geography_by_key: dict[str, Geography],
) -> Song:
    time_period = time_period_by_key.get(song.time.id)
    primary_geography = geography_by_key.get(song.geography.primary.id)
    return Song(
        title=song.title,
        artist=song.artist,
        city=song.city,
        country=song.country,
        time_period_id=time_period.id if time_period else None,
        primary_geography_id=primary_geography.id if primary_geography else None,
        notes=json.dumps(song.model_dump()),
    )


def _seed_song_links(
    db: Session,
    song_row: Song,
    song: PlaylistSongSchema,
    style_by_key: dict[str, Style],
    emotion_by_key: dict[str, Emotion],
    influence_by_key: dict[str, Influence],
    geography_by_key: dict[str, Geography],
) -> None:
    for style in song.styles:
        style_row = style_by_key.get(style.id)
        if style_row is None:
            continue
        db.add(
            SongStyle(
                song_id=song_row.id,
                style_id=style_row.id,
                role=style.role,
                confidence=style.confidence,
            )
        )

    for emotion in song.emotions:
        emotion_row = emotion_by_key.get(emotion.id)
        if emotion_row is None:
            continue
        db.add(
            SongEmotion(
                song_id=song_row.id,
                emotion_id=emotion_row.id,
                confidence=emotion.confidence,
            )
        )

    for influence in song.influences:
        influence_row = influence_by_key.get(influence.id)
        if influence_row is None:
            continue
        db.add(
            SongInfluence(
                song_id=song_row.id,
                influence_id=influence_row.id,
                confidence=influence.confidence,
            )
        )

    for geography in song.geography.secondary:
        geography_row = geography_by_key.get(geography.id)
        if geography_row is None:
            continue
        db.add(
            SongSecondaryGeography(
                song_id=song_row.id,
                geography_id=geography_row.id,
            )
        )


def _lookup_by_key(db: Session) -> tuple[
    dict[str, Style],
    dict[str, Emotion],
    dict[str, Influence],
    dict[str, Geography],
    dict[str, TimePeriod],
]:
    style_by_key = {row.key: row for row in db.scalars(select(Style))}
    emotion_by_key = {row.key: row for row in db.scalars(select(Emotion))}
    influence_by_key = {row.key: row for row in db.scalars(select(Influence))}
    geography_by_key = {row.key: row for row in db.scalars(select(Geography))}
    time_period_by_key = {row.key: row for row in db.scalars(select(TimePeriod))}
    return style_by_key, emotion_by_key, influence_by_key, geography_by_key, time_period_by_key


def _song_ids_for_playlist(db: Session, playlist_id: int) -> list[int]:
    return list(
        db.scalars(
            select(PlaylistSong.song_id).where(PlaylistSong.playlist_id == playlist_id)
        )
    )


def _delete_song_graph(db: Session, song_ids: list[int]) -> None:
    if not song_ids:
        return
    db.execute(delete(SongStyle).where(SongStyle.song_id.in_(song_ids)))
    db.execute(delete(SongEmotion).where(SongEmotion.song_id.in_(song_ids)))
    db.execute(delete(SongInfluence).where(SongInfluence.song_id.in_(song_ids)))
    db.execute(delete(SongSecondaryGeography).where(SongSecondaryGeography.song_id.in_(song_ids)))
    db.execute(delete(Song).where(Song.id.in_(song_ids)))


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
                song_payload = json.loads(row.notes)
                song_payload["song_id"] = link.song_id
                song_payload["position"] = link.position
                song_payload["album"] = row.album
                song_payload["album_cover_url"] = row.album_cover_url
                song_payload["release_year"] = row.release_year
                song_payload["duration_seconds"] = row.duration_seconds
                song_payload["language"] = row.language
                song_payload["lyrics_text"] = row.lyrics_text
                song_payload["notes"] = row.notes
                song_payload["time_period_id"] = row.time_period_id
                song_payload["primary_geography_id"] = row.primary_geography_id
                song_payload["city"] = row.city
                song_payload["country"] = row.country
                song_payload["created_at"] = row.created_at
                songs.append(song_payload)
                continue
            except json.JSONDecodeError:
                pass
        songs.append(
            {
                "song_id": link.song_id,
                "position": link.position,
                "title": row.title,
                "artist": row.artist,
                "album": row.album,
                "album_cover_url": row.album_cover_url,
                "release_year": row.release_year,
                "duration_seconds": row.duration_seconds,
                "language": row.language,
                "lyrics_text": row.lyrics_text,
                "notes": row.notes,
                "time_period_id": row.time_period_id,
                "primary_geography_id": row.primary_geography_id,
                "location": row.location,
                "created_at": row.created_at,
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
        llm_prompt=row.llm_prompt,
        songs=[],
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def create_playlist(db: Session, payload: PlaylistCreate) -> PlaylistStoredRead:
    now = datetime.now(timezone.utc)
    row = Playlist(
        title=payload.title,
        user_prompt=payload.user_prompt,
        llm_prompt=payload.llm_prompt,
        songs_json=json.dumps([song.model_dump() for song in payload.songs]),
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    style_by_key, emotion_by_key, influence_by_key, geography_by_key, time_period_by_key = _lookup_by_key(db)
    for idx, song in enumerate(payload.songs):
        song_row = _song_schema_to_song_row(song, time_period_by_key, geography_by_key)
        db.add(song_row)
        db.flush()
        _seed_song_links(
            db,
            song_row,
            song,
            style_by_key,
            emotion_by_key,
            influence_by_key,
            geography_by_key,
        )
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
    row.llm_prompt = payload.llm_prompt
    row.songs_json = json.dumps([song.model_dump() for song in payload.songs])
    row.updated_at = datetime.now(timezone.utc)
    old_song_ids = _song_ids_for_playlist(db, row.id)
    db.execute(delete(PlaylistSong).where(PlaylistSong.playlist_id == row.id))
    _delete_song_graph(db, old_song_ids)
    db.flush()
    style_by_key, emotion_by_key, influence_by_key, geography_by_key, time_period_by_key = _lookup_by_key(db)
    for idx, song in enumerate(payload.songs):
        song_row = _song_schema_to_song_row(song, time_period_by_key, geography_by_key)
        db.add(song_row)
        db.flush()
        _seed_song_links(
            db,
            song_row,
            song,
            style_by_key,
            emotion_by_key,
            influence_by_key,
            geography_by_key,
        )
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
    song_ids = _song_ids_for_playlist(db, row.id)
    db.execute(delete(PlaylistSong).where(PlaylistSong.playlist_id == row.id))
    _delete_song_graph(db, song_ids)
    db.delete(row)
    db.commit()
    return True
