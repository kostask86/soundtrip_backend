import json
import ssl
from base64 import b64encode
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.tables import Song
from app.schemas.song import SongCreate, SongUpdate

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_SEARCH_URL = "https://api.spotify.com/v1/search"
MUSICBRAINZ_ARTIST_SEARCH_URL = "https://musicbrainz.org/ws/2/artist"
USER_AGENT = "soundtrip-backend/1.0 (local-dev)"


def _musicbrainz_user_agent() -> str:
    contact = settings.musicbrainz_contact_url.strip()
    if not contact:
        contact = "https://github.com/soundtrip/soundtrip_backend"
    return f"soundtrip-backend/1.0 ({contact})"


def _escape_lucene_artist_phrase(artist: str) -> str:
    """Escape backslashes and double quotes for a Lucene phrase inside artist:\"...\"."""
    return artist.replace("\\", "\\\\").replace('"', '\\"')


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


def _set_if(song: Song, field: str, value, overwrite: bool) -> None:
    if value is None:
        return
    current = getattr(song, field)
    if overwrite or current in (None, ""):
        setattr(song, field, value)


def _spotify_token() -> str:
    client_id = settings.spotify_client_id.strip()
    client_secret = settings.spotify_client_secret.strip()
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Spotify credentials are missing. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET.",
        )
    auth = b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8")
    body = urlencode({"grant_type": "client_credentials"}).encode("utf-8")
    req = Request(SPOTIFY_TOKEN_URL, data=body, method="POST")
    req.add_header("Authorization", f"Basic {auth}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Accept", "application/json")
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    try:
        with urlopen(req, timeout=20, context=ssl_context) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Spotify token error: {exc.code}") from None
    except URLError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Network error while calling Spotify token endpoint: {exc.reason}",
        ) from None
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Spotify token response missing access_token")
    return token


def _spotify_track(song: Song) -> dict:
    token = _spotify_token()
    query = f'track:"{song.title}" artist:"{song.artist}"'
    url = f"{SPOTIFY_SEARCH_URL}?{urlencode({'q': query, 'type': 'track', 'limit': 1})}"
    req = Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", USER_AGENT)
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    try:
        with urlopen(req, timeout=20, context=ssl_context) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Spotify search error: {exc.code}") from None
    except URLError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Network error while calling Spotify search endpoint: {exc.reason}",
        ) from None
    items = payload.get("tracks", {}).get("items", [])
    if not items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No Spotify track found for this song")
    return items[0]


def _release_year(date_raw: str | None) -> int | None:
    if not isinstance(date_raw, str):
        return None
    if len(date_raw) >= 4 and date_raw[:4].isdigit():
        return int(date_raw[:4])
    return None


def _musicbrainz_artist_begin_area(artist: str) -> str | None:
    """Resolve begin-area (city) from MusicBrainz artist search; first hit only if score is 100."""
    name = artist.strip()
    if not name:
        return None
    lucene = f'artist:"{_escape_lucene_artist_phrase(name)}"'
    url = f"{MUSICBRAINZ_ARTIST_SEARCH_URL}?{urlencode({'query': lucene, 'fmt': 'json', 'limit': '5'})}"
    req = Request(url)
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", _musicbrainz_user_agent())
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    try:
        with urlopen(req, timeout=20, context=ssl_context) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"MusicBrainz artist search error: {exc.code}",
        ) from None
    except URLError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Network error while calling MusicBrainz: {exc.reason}",
        ) from None
    artists = payload.get("artists")
    if not isinstance(artists, list) or not artists:
        return None
    first = artists[0]
    if not isinstance(first, dict) or first.get("score") != 100:
        return None
    begin = first.get("begin-area")
    if not isinstance(begin, dict):
        return None
    city = begin.get("name")
    if isinstance(city, str) and city.strip():
        return city.strip()
    return None


def apply_spotify_metadata(db: Session, song: Song) -> Song:
    track = _spotify_track(song)
    album = track.get("album", {}) if isinstance(track.get("album"), dict) else {}
    images = album.get("images", []) if isinstance(album.get("images"), list) else []
    cover_url = None
    if images and isinstance(images[0], dict):
        cover_url = images[0].get("url")

    album_title = album.get("name")
    duration_ms = track.get("duration_ms")
    duration_seconds = int(round(duration_ms / 1000)) if isinstance(duration_ms, int) and duration_ms > 0 else None
    release_year = _release_year(album.get("release_date"))

    _set_if(song, "album", album_title, True)
    _set_if(song, "album_cover_url", cover_url, True)
    _set_if(song, "duration_seconds", duration_seconds, True)
    _set_if(song, "release_year", release_year, True)

    # MusicBrainz allows ~1 request/second per client; this path runs after Spotify (single song).
    song.location = _musicbrainz_artist_begin_area(song.artist)

    db.commit()
    db.refresh(song)
    return song
