#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
[ -f ".env" ] || { echo "ERRO: .env não encontrado."; exit 1; }
set -a; source .env; set +a
: "${POSTGRES_DB:?POSTGRES_DB vazio}"
: "${POSTGRES_USER:?POSTGRES_USER vazio}"
: "${BACKUP_RETENTION_LOCAL_DAYS:=7}"
: "${BACKUP_REQUIRE_ENCRYPTION:=true}"
if [ "$BACKUP_REQUIRE_ENCRYPTION" = "true" ] && [ -z "${BACKUP_ENCRYPTION_PASSPHRASE:-}" ]; then
  echo "ERRO: BACKUP_REQUIRE_ENCRYPTION=true, mas BACKUP_ENCRYPTION_PASSPHRASE está vazia."
  exit 1
fi
BACKUP_DIR="${PROJECT_DIR}/backups"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
TS="$(date -u +"%Y%m%dT%H%M%SZ")"
RAW_FILE="${BACKUP_DIR}/${POSTGRES_DB}_${TS}.sql"
GZ_FILE="${RAW_FILE}.gz"
ENC_FILE="${GZ_FILE}.gpg"
echo "==> Gerando pg_dump..."
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "$RAW_FILE"
echo "==> Compactando..."
gzip "$RAW_FILE"
if [ -n "${BACKUP_ENCRYPTION_PASSPHRASE:-}" ]; then
  echo "==> Criptografando..."
  gpg --batch --yes --passphrase "$BACKUP_ENCRYPTION_PASSPHRASE" --symmetric --cipher-algo AES256 -o "$ENC_FILE" "$GZ_FILE"
  rm -f "$GZ_FILE"
  FINAL_FILE="$ENC_FILE"
else
  echo "AVISO: backup sem criptografia permitido apenas porque BACKUP_REQUIRE_ENCRYPTION != true."
  FINAL_FILE="$GZ_FILE"
fi
chmod 600 "$FINAL_FILE"
find "$BACKUP_DIR" -type f -mtime +"$BACKUP_RETENTION_LOCAL_DAYS" -delete
echo "Backup gerado: $FINAL_FILE"
if command -v rclone >/dev/null 2>&1 && [ -n "${BACKBLAZE_BUCKET:-}" ]; then
  rclone copy "$FINAL_FILE" "b2:${BACKBLAZE_BUCKET}/postgres/"
else
  echo "AVISO: rclone/B2 não configurado; off-site não executado nesta rodada."
fi
