#!/usr/bin/env python3
import subprocess
from pathlib import Path


def main() -> int:
    project_dir = Path(__file__).resolve().parents[1]
    command = ["docker", "compose", "exec", "-T", "portal-api", "python", "-m", "app.seed_pilot"]
    return subprocess.call(command, cwd=project_dir)


if __name__ == "__main__":
    raise SystemExit(main())
