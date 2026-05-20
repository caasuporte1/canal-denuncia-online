#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
[ -f ".env" ] || { echo "ERRO: .env não encontrado."; exit 1; }
set -a; source .env; set +a
: "${POSTGRES_USER:?POSTGRES_USER vazio}"
: "${POSTGRES_DB:?POSTGRES_DB vazio}"
BACKUP_DIR="${PROJECT_DIR}/backups"
LATEST_FILE="${1:-}"
[ -n "$LATEST_FILE" ] || LATEST_FILE="$(ls -1t "$BACKUP_DIR"/* 2>/dev/null | head -n 1 || true)"
[ -n "$LATEST_FILE" ] && [ -f "$LATEST_FILE" ] || { echo "ERRO: nenhum backup encontrado."; exit 1; }
TMP_DB="restore_test_$(date -u +"%Y%m%d%H%M%S")"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
RESTORE_SQL="${TMP_DIR}/restore.sql"
case "$LATEST_FILE" in
  *.gpg)
    [ -n "${BACKUP_ENCRYPTION_PASSPHRASE:-}" ] || { echo "ERRO: passphrase vazia."; exit 1; }
    gpg --batch --yes --passphrase "$BACKUP_ENCRYPTION_PASSPHRASE" -o "${TMP_DIR}/restore.sql.gz" -d "$LATEST_FILE"
    gunzip -c "${TMP_DIR}/restore.sql.gz" > "$RESTORE_SQL"
    ;;
  *.gz) gunzip -c "$LATEST_FILE" > "$RESTORE_SQL" ;;
  *.sql) cp "$LATEST_FILE" "$RESTORE_SQL" ;;
  *) echo "ERRO: extensão não suportada."; exit 1 ;;
esac
ORIGINAL_TABLE_COUNT="$(docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")"
ORIGINAL_INDEX_COUNT="$(docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT count(*) FROM pg_indexes WHERE schemaname='public';")"
docker compose exec -T postgres createdb -U "$POSTGRES_USER" "$TMP_DB"
docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$TMP_DB" < "$RESTORE_SQL" >/dev/null
RESTORED_TABLE_COUNT="$(docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$TMP_DB" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")"
RESTORED_INDEX_COUNT="$(docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$TMP_DB" -tAc "SELECT count(*) FROM pg_indexes WHERE schemaname='public';")"
REQUIRED_INDEXES="$(docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$TMP_DB" -tAc "SELECT count(*) FROM pg_indexes WHERE schemaname='public' AND indexname IN ('ix_reports_protocol','ix_attachments_report_active','ix_audit_logs_report_not_null','ix_email_notifications_pending');")"
docker compose exec -T postgres dropdb -U "$POSTGRES_USER" "$TMP_DB"
if [ "$ORIGINAL_TABLE_COUNT" != "$RESTORED_TABLE_COUNT" ]; then
  echo "ERRO: tabelas restauradas ($RESTORED_TABLE_COUNT) diferem do original ($ORIGINAL_TABLE_COUNT)."
  exit 1
fi
if [ "$ORIGINAL_INDEX_COUNT" != "$RESTORED_INDEX_COUNT" ]; then
  echo "ERRO: índices restaurados ($RESTORED_INDEX_COUNT) diferem do original ($ORIGINAL_INDEX_COUNT)."
  exit 1
fi
if [ "$REQUIRED_INDEXES" -lt 4 ]; then
  echo "ERRO: índices críticos ausentes no restore."
  exit 1
fi
[ "$ORIGINAL_TABLE_COUNT" != "0" ] || echo "AVISO: banco ainda vazio; na Sprint com schema real deverá validar tabelas > 0."
echo "Restore testado com sucesso. tabelas=$RESTORED_TABLE_COUNT indices=$RESTORED_INDEX_COUNT indices_criticos=$REQUIRED_INDEXES"
