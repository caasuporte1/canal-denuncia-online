from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.report import Report

_DUMMY_HASH = hash_password("dummy-password-for-constant-time-check")


def verify_credentials_constant_time(db: Session, protocol: str, login: str, password: str) -> bool:
    report = db.scalar(
        select(Report).where(
            Report.protocol == protocol,
            Report.access_login == login,
        )
    )
    password_hash = report.access_password_hash if report else _DUMMY_HASH
    valid_password = verify_password(password, password_hash)

    # TODO Sprint 4:
    # Usar esta função no endpoint de acompanhamento da denúncia para mitigar timing attack.
    # O endpoint deve retornar mensagem genérica única, sem revelar se protocolo, login ou senha falhou.
    return bool(report and valid_password)
