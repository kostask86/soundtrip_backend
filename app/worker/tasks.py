from app.core.database import SessionLocal
from app.models.tables import Song
from app.schemas.playlist import PlaylistCreate
from app.services.playlist_generator import generate_playlist
from app.services.playlists import create_playlist
from app.services.similar_songs_generator import generate_similar_songs
from app.worker.celery_app import celery_app


@celery_app.task(name="generate_playlist_task")
def generate_playlist_task(user_prompt: str) -> dict:
    db = SessionLocal()
    try:
        generated, llm_prompt = generate_playlist(user_prompt=user_prompt)
        created = create_playlist(
            db,
            PlaylistCreate(
                title=None,
                user_prompt=generated.user_prompt,
                llm_prompt=llm_prompt,
                songs=generated.songs,
            ),
        )
        return {"playlist_id": created.id, "playlist": created.model_dump(mode="json")}
    finally:
        db.close()


@celery_app.task(name="generate_similar_songs_task")
def generate_similar_songs_task(song_id: int, count: int, radius_km: int) -> dict:
    db = SessionLocal()
    try:
        generated, llm_prompt = generate_similar_songs(
            db, song_id=song_id, count=count, radius_km=radius_km
        )
        song = db.get(Song, song_id)
        title = f"Similar: {song.title}"[:255] if song is not None else None
        created = create_playlist(
            db,
            PlaylistCreate(
                title=title,
                user_prompt=generated.user_prompt,
                llm_prompt=llm_prompt,
                songs=generated.songs,
            ),
        )
        return {"playlist_id": created.id, "playlist": created.model_dump(mode="json")}
    finally:
        db.close()
