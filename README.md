# soundtrip_backend

Sound Trip app backend built with FastAPI, SQLAlchemy, Alembic, and SQLite.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Database

Run the single Alembic revision:

```bash
alembic upgrade head
```

Create tables directly from models metadata (bootstrap utility script):

```bash
python scripts/create_db_tables.py
```

## Run API

```bash
python run.py
```

This starts:
- Broker (`CELERY_BROKER_COMMAND`, default `redis-server`)
- Celery worker (queue: `CELERY_QUEUE_NAME`)
- Flower UI (`http://localhost:5555` by default)
- FastAPI app (`http://localhost:8000`)

## OpenAPI

- Generated OpenAPI spec file: `openapi.json`
- Interactive docs (while server is running): `http://localhost:8000/docs`

## Current API routes

- `GET /health`
- `POST /api/v1/songs`
- `GET /api/v1/songs`
- `GET /api/v1/songs/{song_id}`
- `PUT /api/v1/songs/{song_id}`
- `DELETE /api/v1/songs/{song_id}`
- `POST /api/v1/styles`
- `GET /api/v1/styles`
- `GET /api/v1/styles/{style_id}`
- `PUT /api/v1/styles/{style_id}`
- `DELETE /api/v1/styles/{style_id}`
- `POST /api/v1/emotions`
- `GET /api/v1/emotions`
- `GET /api/v1/emotions/{emotion_id}`
- `PUT /api/v1/emotions/{emotion_id}`
- `DELETE /api/v1/emotions/{emotion_id}`
- `POST /api/v1/influences`
- `GET /api/v1/influences`
- `GET /api/v1/influences/{influence_id}`
- `PUT /api/v1/influences/{influence_id}`
- `DELETE /api/v1/influences/{influence_id}`
- `POST /api/v1/geographies`
- `GET /api/v1/geographies`
- `GET /api/v1/geographies/{geography_id}`
- `PUT /api/v1/geographies/{geography_id}`
- `DELETE /api/v1/geographies/{geography_id}`

## Async Playlist Generation (Queue)

Only playlist generation is queued. All other endpoints remain direct/synchronous.

### Start a generation job

```bash
curl -X POST "http://localhost:8000/api/v1/playlists/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "I want 5 rock songs that talk about political rebellion from Scandinavia"
  }'
```

Response (example):

```json
{
  "job_id": "3c0e6f57-....",
  "status": "queued"
}
```

### Poll job status/result

```bash
curl "http://localhost:8000/api/v1/playlists/jobs/<job_id>"
```

When completed, the response includes `playlist_id` and `playlist`.

### Monitor queue in browser

- Flower dashboard: `http://localhost:5555`
- You can inspect tasks, states, runtime, and failures there.
