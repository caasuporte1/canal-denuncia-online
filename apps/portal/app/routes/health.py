import shutil
import time

from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import SessionLocal
from app.core.session import redis_client

START_TIME = time.monotonic()

router = APIRouter()


@router.get("/health")
def health() -> dict:
    checks = {
        "postgres": _postgres_check(),
        "redis": _redis_check(),
        "disk": _disk_check(),
    }
    status = "ok" if all(value == "ok" for value in checks.values()) else "degraded"
    return {
        "service": "Canal de Denuncia Online",
        "status": status,
        "uptime_seconds": int(time.monotonic() - START_TIME),
        "checks": checks,
    }


def _postgres_check() -> str:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"


def _redis_check() -> str:
    try:
        return "ok" if redis_client.ping() else "error"
    except Exception:
        return "error"


def _disk_check() -> str:
    usage = shutil.disk_usage("/")
    used_ratio = usage.used / usage.total
    return "ok" if used_ratio < 0.90 else "warning"
