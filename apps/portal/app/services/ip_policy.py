import hashlib

from fastapi import Request

from app.core.config import settings


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"


def anonymous_ip_hash(ip_address: str) -> str:
    return hashlib.sha256(f"{settings.salt_ip_hash}{ip_address}".encode("utf-8")).hexdigest()
