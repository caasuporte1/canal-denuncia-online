import json
import secrets
from dataclasses import dataclass
from uuid import UUID

import redis
from fastapi import Request, Response

from app.core.config import settings

redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


@dataclass(frozen=True)
class SessionData:
    session_id: str
    user_id: UUID
    tenant_id: UUID | None
    role: str
    csrf_token: str


@dataclass(frozen=True)
class ComplainantSessionData:
    session_id: str
    report_id: UUID
    tenant_id: UUID
    csrf_token: str


def create_session(response: Response, *, user_id, tenant_id, role: str) -> SessionData:
    session_id = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    payload = {
        "user_id": str(user_id),
        "tenant_id": str(tenant_id) if tenant_id else None,
        "role": role,
        "csrf_token": csrf_token,
    }
    redis_client.setex(_key(session_id), settings.session_ttl_seconds, json.dumps(payload))
    response.set_cookie(
        settings.session_cookie_name,
        session_id,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=True,
        samesite="strict",
    )
    return SessionData(session_id=session_id, user_id=user_id, tenant_id=tenant_id, role=role, csrf_token=csrf_token)


def get_session(request: Request) -> SessionData | None:
    session_id = request.cookies.get(settings.session_cookie_name)
    if not session_id:
        return None
    raw = redis_client.get(_key(session_id))
    if not raw:
        return None
    payload = json.loads(raw)
    redis_client.expire(_key(session_id), settings.session_ttl_seconds)
    return SessionData(
        session_id=session_id,
        user_id=UUID(payload["user_id"]),
        tenant_id=UUID(payload["tenant_id"]) if payload.get("tenant_id") else None,
        role=payload["role"],
        csrf_token=payload["csrf_token"],
    )


def destroy_session(request: Request, response: Response) -> None:
    session_id = request.cookies.get(settings.session_cookie_name)
    if session_id:
        redis_client.delete(_key(session_id))
    response.delete_cookie(settings.session_cookie_name, httponly=True, secure=True, samesite="strict")


def verify_csrf(request: Request, token: str) -> bool:
    session = get_session(request)
    return bool(session and secrets.compare_digest(session.csrf_token, token))


def create_complainant_session(response: Response, *, report_id, tenant_id) -> ComplainantSessionData:
    session_id = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    payload = {
        "report_id": str(report_id),
        "tenant_id": str(tenant_id),
        "csrf_token": csrf_token,
    }
    redis_client.setex(_complainant_key(session_id), settings.complainant_session_ttl_seconds, json.dumps(payload))
    response.set_cookie(
        settings.complainant_session_cookie_name,
        session_id,
        max_age=settings.complainant_session_ttl_seconds,
        httponly=True,
        secure=True,
        samesite="strict",
    )
    return ComplainantSessionData(session_id=session_id, report_id=report_id, tenant_id=tenant_id, csrf_token=csrf_token)


def get_complainant_session(request: Request) -> ComplainantSessionData | None:
    session_id = request.cookies.get(settings.complainant_session_cookie_name)
    if not session_id:
        return None
    raw = redis_client.get(_complainant_key(session_id))
    if not raw:
        return None
    payload = json.loads(raw)
    redis_client.expire(_complainant_key(session_id), settings.complainant_session_ttl_seconds)
    return ComplainantSessionData(
        session_id=session_id,
        report_id=UUID(payload["report_id"]),
        tenant_id=UUID(payload["tenant_id"]),
        csrf_token=payload["csrf_token"],
    )


def destroy_complainant_session(request: Request, response: Response) -> None:
    session_id = request.cookies.get(settings.complainant_session_cookie_name)
    if session_id:
        redis_client.delete(_complainant_key(session_id))
    response.delete_cookie(settings.complainant_session_cookie_name, httponly=True, secure=True, samesite="strict")


def verify_complainant_csrf(request: Request, token: str) -> bool:
    session = get_complainant_session(request)
    return bool(session and secrets.compare_digest(session.csrf_token, token))


def _key(session_id: str) -> str:
    return f"session:{session_id}"


def _complainant_key(session_id: str) -> str:
    return f"complainant_session:{session_id}"
