#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
echo "== Containers =="
docker compose ps
echo "== Banco de dados =="
docker compose exec -T postgres pg_isready -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-postgres}" >/dev/null && echo "postgres=ok" || echo "postgres=erro"
docker compose exec -T redis sh -c 'redis-cli ${REDIS_PASSWORD:+-a "$REDIS_PASSWORD"} ping' 2>/dev/null | sed 's/^/redis=/' || echo "redis=erro"
echo "== Totais operacionais =="
docker compose exec -T postgres psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-postgres}" -Atc "select 'tenants=' || count(*) from tenants;" 2>/dev/null || true
docker compose exec -T postgres psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-postgres}" -Atc "select 'denuncias=' || count(*) from reports;" 2>/dev/null || true
docker compose exec -T postgres psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-postgres}" -Atc "select 'denuncias_' || status || '=' || count(*) from reports group by status order by status;" 2>/dev/null || true
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
