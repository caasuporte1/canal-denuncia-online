#!/usr/bin/env bash
set -euo pipefail
# DEV ONLY: cria tenant e usuário de teste. Não usar em produção.
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
docker compose exec -T portal-api python -m app.seed
