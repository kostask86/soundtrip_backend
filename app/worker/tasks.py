from app.core.database import SessionLocal
from app.schemas.playlist import PlaylistCreate
from app.services.playlist_generator import generate_playlist
from app.services.playlists import create_playlist
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
        return {"playlist_id": created.id}
    finally:
        db.close()
