from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import SessionDep
from app.core.config import settings
from app.schemas.playlist import (
    PlaylistCreate,
    PlaylistGenerationJobResponse,
    PlaylistJobStatusResponse,
    PlaylistRequest,
    PlaylistStoredRead,
    PlaylistUpdate,
    SimilarSongsRequest,
)
from app.services.playlists import create_playlist, delete_playlist, get_playlist, list_playlists, update_playlist
from app.services.songs import get_song
from app.worker.celery_app import celery_app
from app.worker.tasks import generate_playlist_task, generate_similar_songs_task

router = APIRouter(prefix="/playlists", tags=["playlists"])


@router.post("/generate", response_model=PlaylistGenerationJobResponse, status_code=status.HTTP_202_ACCEPTED)
def generate_playlist_from_prompt(payload: PlaylistRequest) -> PlaylistGenerationJobResponse:
    task = generate_playlist_task.apply_async(
        args=[payload.prompt],
        queue=settings.celery_queue_name,
    )
    return PlaylistGenerationJobResponse(job_id=task.id, status="queued")


@router.post("/generate/similar", response_model=PlaylistGenerationJobResponse, status_code=status.HTTP_202_ACCEPTED)
def generate_similar_songs_from_anchor(
    db: SessionDep,
    payload: SimilarSongsRequest,
) -> PlaylistGenerationJobResponse:
    song = get_song(db, payload.song_id)
    if song is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    if not (song.city and str(song.city).strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Song has no city; cannot anchor similar-by-city.",
        )
    task = generate_similar_songs_task.apply_async(
        args=[payload.song_id, payload.count],
        queue=settings.celery_queue_name,
    )
    return PlaylistGenerationJobResponse(job_id=task.id, status="queued")


@router.get("/jobs/{job_id}", response_model=PlaylistJobStatusResponse)
def get_playlist_generation_job(db: SessionDep, job_id: str) -> PlaylistJobStatusResponse:
    result = AsyncResult(job_id, app=celery_app)
    status_value = (result.status or "PENDING").lower()
    response = PlaylistJobStatusResponse(job_id=job_id, status=status_value)
    if status_value == "success":
        payload = result.result if isinstance(result.result, dict) else {}
        playlist_id = payload.get("playlist_id")
        response.playlist_id = playlist_id
        playlist_payload = payload.get("playlist")
        if isinstance(playlist_payload, dict):
            response.playlist = PlaylistStoredRead.model_validate(playlist_payload)
        elif isinstance(playlist_id, int):
            response.playlist = get_playlist(db, playlist_id)
    elif status_value in {"failure", "revoked"}:
        response.error = str(result.result)
    return response


@router.post("", response_model=PlaylistStoredRead, status_code=status.HTTP_201_CREATED)
def create_playlist_endpoint(db: SessionDep, payload: PlaylistCreate) -> PlaylistStoredRead:
    return create_playlist(db, payload)


@router.get("", response_model=list[PlaylistStoredRead])
def list_playlists_endpoint(
    db: SessionDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[PlaylistStoredRead]:
    return list_playlists(db, limit=limit, offset=offset)


@router.get("/{playlist_id}", response_model=PlaylistStoredRead)
def get_playlist_endpoint(db: SessionDep, playlist_id: int) -> PlaylistStoredRead:
    row = get_playlist(db, playlist_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")
    return row


@router.put("/{playlist_id}", response_model=PlaylistStoredRead)
def update_playlist_endpoint(db: SessionDep, playlist_id: int, payload: PlaylistUpdate) -> PlaylistStoredRead:
    row = update_playlist(db, playlist_id, payload)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")
    return row


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_playlist_endpoint(db: SessionDep, playlist_id: int) -> None:
    deleted = delete_playlist(db, playlist_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")
