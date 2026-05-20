from sqlalchemy import select

import app.models
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User


def seed() -> None:
    db = SessionLocal()
    try:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == "triton"))
        if not tenant:
            tenant = Tenant(
                name="Triton SST",
                document="00000000000000",
                slug="triton",
                status="active",
            )
            db.add(tenant)
            db.flush()
        admin = db.scalar(select(User).where(User.tenant_id == tenant.id, User.email == "admin-triton@example.invalid"))
        if not admin:
            db.add(
                User(
                    tenant_id=tenant.id,
                    name="Admin Triton",
                    email="admin-triton@example.invalid",
                    password_hash=hash_password("dev-only-change-me"),
                    role="tenant_admin",
                    status="active",
                )
            )
        db.commit()
        print("Seed de desenvolvimento aplicado.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
