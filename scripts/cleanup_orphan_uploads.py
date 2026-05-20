#!/usr/bin/env python3
import argparse
import subprocess


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    cmd = ["docker", "compose", "exec", "-T", "portal-api", "python", "-m", "app.services.maintenance_cli", "orphans"]
    if args.dry_run:
        cmd.append("--dry-run")
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
