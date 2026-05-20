import os
import secrets
from functools import lru_cache


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


class Settings:
    def __init__(self) -> None:
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.database_url = _normalize_database_url(os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://canal_user:canal_password@postgres:5432/canal_denuncia",
        ))
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.session_cookie_name = os.getenv("SESSION_COOKIE_NAME", "cdo_session")
        self.session_ttl_seconds = int(os.getenv("SESSION_TTL_SECONDS", str(8 * 60 * 60)))
        self.complainant_session_cookie_name = os.getenv("COMPLAINANT_SESSION_COOKIE_NAME", "cdo_complainant_session")
        self.complainant_session_ttl_seconds = int(os.getenv("COMPLAINANT_SESSION_TTL_SECONDS", str(30 * 60)))
        self.session_secret = os.getenv("SESSION_SECRET", "")
        if self.environment == "production" and not self.session_secret:
            raise RuntimeError("SESSION_SECRET precisa estar configurado em production.")
        if not self.session_secret:
            self.session_secret = secrets.token_urlsafe(32)
        self.domain_portal = os.getenv("DOMAIN_PORTAL", "localhost")
        self.smtp_host = os.getenv("BREVO_SMTP_HOST", "")
        self.smtp_port = int(os.getenv("BREVO_SMTP_PORT", "587") or "587")
        self.smtp_user = os.getenv("BREVO_SMTP_USER", "")
        self.smtp_password = os.getenv("BREVO_SMTP_PASSWORD", "")
        self.smtp_from_email = os.getenv("SMTP_FROM_EMAIL", "")
        self.smtp_from_name = os.getenv("SMTP_FROM_NAME", "Canal de Denuncia Online")
        self.salt_ip_hash = os.getenv("SALT_IP_HASH", "")
        if self.environment == "production" and not self.salt_ip_hash:
            raise RuntimeError("SALT_IP_HASH precisa estar configurado em production.")
        if not self.salt_ip_hash:
            self.salt_ip_hash = secrets.token_urlsafe(32)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
