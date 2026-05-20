#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
echo "== Containers =="
docker compose ps
echo "== Disco =="
df -h /
echo "== Memoria =="
free -h
echo "== Uptime =="
uptime
echo "== Uploads =="
docker compose exec -T portal-api sh -c 'du -sh /app/uploads 2>/dev/null || true'
echo "== Ultimos backups =="
find backups -maxdepth 1 -type f -printf '%TY-%Tm-%Td %TH:%TM %s %p\n' 2>/dev/null | sort | tail -5 || true
