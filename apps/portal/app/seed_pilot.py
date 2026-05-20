from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User
from app.services.credentials import generate_password


@dataclass(frozen=True)
class PilotTenant:
    slug: str
    name: str
    document: str


PILOT_TENANTS = [
    PilotTenant(slug="alpha-industria", name="Alpha Indústria", document="10000000000001"),
    PilotTenant(slug="beta-logistica", name="Beta Logística", document="10000000000002"),
    PilotTenant(slug="gamma-saude", name="Gamma Saúde", document="10000000000003"),
]


def _ensure_user(db: Session, tenant: Tenant, email: str, name: str, role: str) -> tuple[str, str | None]:
    existing = db.scalar(select(User).where(User.tenant_id == tenant.id, User.email == email))
    if existing:
        return "exists", None

    password = generate_password()
    db.add(
        User(
            tenant_id=tenant.id,
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=role,
            status="active",
        )
    )
    return "created", password


def seed_pilot_tenants() -> list[dict[str, str | None]]:
    """DEV/PILOT ONLY: creates fake pilot tenants and temporary credentials."""
    results: list[dict[str, str | None]] = []
    db = SessionLocal()
    try:
        for item in PILOT_TENANTS:
            tenant = db.scalar(select(Tenant).where(Tenant.slug == item.slug))
            tenant_status = "exists"
            if not tenant:
                tenant = Tenant(name=item.name, document=item.document, slug=item.slug, status="active")
                db.add(tenant)
                db.flush()
                tenant_status = "created"

            admin_status, admin_password = _ensure_user(
                db,
                tenant,
                f"admin@{item.slug}.local",
                f"Admin {item.name}",
                "tenant_admin",
            )
            user_status, user_password = _ensure_user(
                db,
                tenant,
                f"usuario@{item.slug}.local",
                f"Usuário {item.name}",
                "tenant_user",
            )
            results.append(
                {
                    "tenant": item.slug,
                    "tenant_status": tenant_status,
                    "admin_email": f"admin@{item.slug}.local",
                    "admin_status": admin_status,
                    "admin_password": admin_password,
                    "user_email": f"usuario@{item.slug}.local",
                    "user_status": user_status,
                    "user_password": user_password,
                }
            )
        db.commit()
        return results
    finally:
        db.close()


def main() -> None:
    print("DEV/PILOT ONLY - não usar como onboarding de produção.")
    for item in seed_pilot_tenants():
        print(f"tenant={item['tenant']} status={item['tenant_status']}")
        print(f"  admin {item['admin_email']} status={item['admin_status']} password={item['admin_password'] or '(mantida)'}")
        print(f"  user  {item['user_email']} status={item['user_status']} password={item['user_password'] or '(mantida)'}")


if __name__ == "__main__":
    main()
