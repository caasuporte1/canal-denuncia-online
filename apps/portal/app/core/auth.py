from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.session import SessionData, get_session
from app.models.user import User


@dataclass(frozen=True)
class CurrentUser:
    user: User
    session: SessionData


def require_auth(request: Request, db: Session = Depends(get_db)) -> CurrentUser:
    session = get_session(request)
    if not session:
        raise HTTPException(status_code=303, headers={"Location": "/auth/login"})
    user = db.get(User, session.user_id)
    if not user or user.status != "active":
        raise HTTPException(status_code=303, headers={"Location": "/auth/login"})
    return CurrentUser(user=user, session=session)


def require_roles(*roles: str):
    def dependency(current: CurrentUser = Depends(require_auth)) -> CurrentUser:
        if current.user.role not in roles:
            raise HTTPException(status_code=403, detail="Acesso negado.")
        return current

    return dependency
