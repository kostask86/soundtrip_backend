"""Run broker, Celery worker, Flower, and API together for development."""

from __future__ import annotations

import shlex
import signal
import subprocess
import sys
from collections.abc import Sequence

from app.core.config import settings


def _spawn(command: Sequence[str]) -> subprocess.Popen:
    return subprocess.Popen(command)


def main() -> None:
    processes: list[subprocess.Popen] = []
    try:
        # Broker (Redis by default)
        broker_cmd = shlex.split(settings.celery_broker_command or "")
        if broker_cmd:
            processes.append(_spawn(broker_cmd))
        else:
            print("CELERY_BROKER_COMMAND is empty; assuming external broker is already running.")

        # Celery worker
        processes.append(
            _spawn(
                [
                    sys.executable,
                    "-m",
                    "celery",
                    "-A",
                    "app.worker.celery_app.celery_app",
                    "worker",
                    "-l",
                    "info",
                    "-Q",
                    settings.celery_queue_name,
                ]
            )
        )

        # Flower dashboard
        processes.append(
            _spawn(
                [
                    sys.executable,
                    "-m",
                    "celery",
                    "-A",
                    "app.worker.celery_app.celery_app",
                    "flower",
                    f"--port={settings.celery_flower_port}",
                ]
            )
        )

        # FastAPI app
        processes.append(
            _spawn(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    settings.api_host,
                    "--port",
                    str(settings.api_port),
                    *([] if not settings.api_reload else ["--reload"]),
                ]
            )
        )

        for proc in processes:
            proc.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.send_signal(signal.SIGTERM)
        for proc in processes:
            if proc.poll() is None:
                proc.wait(timeout=10)


if __name__ == "__main__":
    main()
