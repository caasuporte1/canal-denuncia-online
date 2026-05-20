import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.report import Report


def _token(prefix: str, size: int) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return f"{prefix}-" + "".join(secrets.choice(alphabet) for _ in range(size))


def generate_protocol(db: Session) -> str:
    while True:
        protocol = _token("CDO", 10)
        exists = db.scalar(select(Report.id).where(Report.protocol == protocol))
        if not exists:
            return protocol
