import json
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import certifi
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Song
from app.schemas.song import SongCreate, SongMetadataApplyRequest, SongMetadataCandidate, SongUpdate

MB_BASE = "https://musicbrainz.org/ws/2"
CAA_BASE = "https://coverartarchive.org"
USER_AGENT = "soundtrip-backend/1.0 (local-dev)"


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


def _http_json(url: str) -> dict:
    req = Request(url)
    req.add_header("User-Agent", USER_AGENT)
    req.add_header("Accept", "application/json")
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    try:
        with urlopen(req, timeout=20, context=ssl_context) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"MusicBrainz HTTP error: {exc.code}",
        ) from None
    except URLError as exc:
        reason = str(exc.reason)
        if "CERTIFICATE_VERIFY_FAILED" in reason:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="TLS certificate verification failed while calling MusicBrainz",
            ) from None
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Network error while calling MusicBrainz: {reason}",
        ) from None


def _first_release_data(recording: dict) -> dict:
    releases = recording.get("releases", [])
    return releases[0] if releases else {}


def _candidate_from_recording(recording: dict) -> SongMetadataCandidate:
    release = _first_release_data(recording)
    release_group = release.get("release-group", {})
    artist_credits = recording.get("artist-credit", [])
    artist_name = artist_credits[0].get("name", "") if artist_credits else ""
    release_mbid = release.get("id")
    release_group_mbid = release_group.get("id")
    cover_preview = f"{CAA_BASE}/release/{release_mbid}/front-250" if release_mbid else None
    return SongMetadataCandidate(
        recording_mbid=recording.get("id", ""),
        recording_title=recording.get("title", ""),
        artist_name=artist_name,
        score=int(recording.get("score", 0)),
        release_mbid=release_mbid,
        release_title=release.get("title"),
        release_date=release.get("date"),
        release_group_mbid=release_group_mbid,
        release_group_title=release_group.get("title"),
        cover_url_preview=cover_preview,
    )


def search_musicbrainz_candidates(song: Song, limit: int = 10) -> list[SongMetadataCandidate]:
    query = f'recording:"{song.title}" AND artist:"{song.artist}"'
    url = f"{MB_BASE}/recording?query={quote(query)}&fmt=json&limit={limit}"
    payload = _http_json(url)
    recordings = payload.get("recordings", [])
    return [_candidate_from_recording(recording) for recording in recordings]


def _cover_url_for(release_mbid: str | None, release_group_mbid: str | None) -> str | None:
    if release_mbid:
        return f"{CAA_BASE}/release/{release_mbid}/front"
    if release_group_mbid:
        return f"{CAA_BASE}/release-group/{release_group_mbid}/front"
    return None


def _set_if(song: Song, field: str, value, overwrite: bool) -> None:
    if value is None:
        return
    current = getattr(song, field)
    if overwrite or current in (None, ""):
        setattr(song, field, value)


def _pick_auto_candidate(song: Song, min_score: int) -> SongMetadataCandidate:
    candidates = search_musicbrainz_candidates(song, limit=10)
    if not candidates:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No MusicBrainz candidates found")
    filtered = [c for c in candidates if c.score >= min_score]
    if not filtered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No candidate passed min_score={min_score}",
        )
    filtered.sort(key=lambda c: c.score, reverse=True)
    return filtered[0]


def _recording_artist(recording_payload: dict) -> str | None:
    artist_credits = recording_payload.get("artist-credit", [])
    return artist_credits[0].get("name") if artist_credits else None


def apply_musicbrainz_metadata(db: Session, song: Song, payload: SongMetadataApplyRequest) -> Song:
    if payload.auto:
        candidate = _pick_auto_candidate(song, payload.min_score)
        recording_mbid = candidate.recording_mbid
        release_mbid = payload.release_mbid or candidate.release_mbid
        release_group_mbid = payload.release_group_mbid or candidate.release_group_mbid
    else:
        if not payload.recording_mbid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="recording_mbid is required when auto=false",
            )
        recording_mbid = payload.recording_mbid
        release_mbid = payload.release_mbid
        release_group_mbid = payload.release_group_mbid

    recording_url = f"{MB_BASE}/recording/{recording_mbid}?fmt=json&inc=releases+artists"
    recording = _http_json(recording_url)

    if not release_mbid:
        first_release = _first_release_data(recording)
        release_mbid = first_release.get("id")
        if not release_group_mbid:
            release_group_mbid = first_release.get("release-group", {}).get("id")

    album_title = None
    release_year = None
    if release_mbid:
        release_url = f"{MB_BASE}/release/{release_mbid}?fmt=json"
        release_payload = _http_json(release_url)
        album_title = release_payload.get("title")
        date_raw = release_payload.get("date", "")
        if len(date_raw) >= 4 and date_raw[:4].isdigit():
            release_year = int(date_raw[:4])
        if not release_group_mbid:
            release_group_mbid = release_payload.get("release-group", {}).get("id")

    cover_url = _cover_url_for(release_mbid, release_group_mbid)

    _set_if(song, "mb_recording_mbid", recording_mbid, payload.overwrite)
    _set_if(song, "mb_release_mbid", release_mbid, payload.overwrite)
    _set_if(song, "mb_release_group_mbid", release_group_mbid, payload.overwrite)
    _set_if(song, "album", album_title, payload.overwrite)
    _set_if(song, "release_year", release_year, payload.overwrite)
    _set_if(song, "album_cover_url", cover_url, payload.overwrite)
    _set_if(song, "artist", _recording_artist(recording), payload.overwrite)

    db.commit()
    db.refresh(song)
    return song
