import argparse

from app.core.database import SessionLocal
from app.core.session import redis_client
from app.services.maintenance import cleanup_orphan_uploads, retention_cleanup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["retention", "orphans", "sessions"])
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args()

    if args.command == "sessions":
        print(session_summary())
        return

    with SessionLocal() as db:
        if args.command == "retention":
            print(retention_cleanup(db, dry_run=args.dry_run))
        elif args.command == "orphans":
            print(cleanup_orphan_uploads(db, dry_run=args.dry_run))


def session_summary() -> dict:
    keys = list(redis_client.scan_iter(match="session:*")) + list(redis_client.scan_iter(match="complainant_session:*"))
    no_ttl = [key for key in keys if redis_client.ttl(key) == -1]
    return {"sessions": len(keys), "without_ttl": len(no_ttl)}


if __name__ == "__main__":
    main()
