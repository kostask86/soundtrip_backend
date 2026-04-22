from fastapi import FastAPI

from app.api.routes import emotions, geographies, health, influences, playlists, songs, styles, time_periods
from app.core.config import settings

app = FastAPI(title=settings.app_name)

app.include_router(health.router)
app.include_router(songs.router, prefix="/api/v1")
app.include_router(styles.router, prefix="/api/v1")
app.include_router(emotions.router, prefix="/api/v1")
app.include_router(influences.router, prefix="/api/v1")
app.include_router(geographies.router, prefix="/api/v1")
app.include_router(time_periods.router, prefix="/api/v1")
app.include_router(playlists.router, prefix="/api/v1")
