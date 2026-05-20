#!/usr/bin/env python3
import subprocess


def main() -> None:
    subprocess.run(
        ["docker", "compose", "exec", "-T", "portal-api", "python", "-m", "app.services.maintenance_cli", "sessions"],
        check=True,
    )


if __name__ == "__main__":
    main()
