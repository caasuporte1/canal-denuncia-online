#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
[ -f ".env" ] || { echo "ERRO: .env não encontrado."; exit 1; }
set -a; source .env; set +a
: "${DOMAIN_PORTAL:?DOMAIN_PORTAL vazio}"
: "${VPS_IP:?VPS_IP vazio}"
echo "==> Testando HTTPS do portal..."
curl -fsS "https://${DOMAIN_PORTAL}/health" >/dev/null
echo "OK: portal HTTPS respondeu /health"
echo "==> Validando PostgreSQL fechado no IP $VPS_IP..."
if nc -z -w 3 "$VPS_IP" 5432; then echo "ERRO: 5432 aberta."; exit 1; else echo "OK: 5432 fechada."; fi
echo "==> Validando Redis fechado no IP $VPS_IP..."
if nc -z -w 3 "$VPS_IP" 6379; then echo "ERRO: 6379 aberta."; exit 1; else echo "OK: 6379 fechada."; fi
docker compose ps
echo "Smoke test concluído."
