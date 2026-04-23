from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import SessionDep
from app.schemas.playlist import PlaylistCreate, PlaylistRequest, PlaylistStoredRead, PlaylistUpdate
from app.services.playlist_generator import generate_playlist
from app.services.playlists import create_playlist, delete_playlist, get_playlist, list_playlists, update_playlist

router = APIRouter(prefix="/playlists", tags=["playlists"])


@router.post("/generate", response_model=PlaylistStoredRead, status_code=status.HTTP_201_CREATED)
def generate_playlist_from_prompt(db: SessionDep, payload: PlaylistRequest) -> PlaylistStoredRead:
    generated, llm_prompt = generate_playlist(user_prompt=payload.prompt)
    create_payload = PlaylistCreate(
        title=None,
        user_prompt=generated.user_prompt,
        llm_prompt=llm_prompt,
        songs=generated.songs,
    )
    return create_playlist(db, create_payload)


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
