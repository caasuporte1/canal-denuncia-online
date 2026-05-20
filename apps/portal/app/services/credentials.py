import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.report import Report


def generate_login(db: Session) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    while True:
        login = "USR-" + "".join(secrets.choice(alphabet) for _ in range(8))
        exists = db.scalar(select(Report.id).where(Report.access_login == login))
        if not exists:
            return login


def generate_password() -> str:
    return secrets.token_urlsafe(18)


def hash_access_password(password: str) -> str:
    return hash_password(password)
