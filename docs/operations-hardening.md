# Hardening operacional Sprint 6

## Logging e rotacao
A aplicacao registra logs estruturados em stdout com `request_id`, metodo, path, status e duracao.
A rotacao do log de acesso/Traefik continua no volume operacional da VPS; para piloto, `ops_summary.sh` permite checagem rapida e a retencao deve ser acompanhada no host.

## Headers
Headers continuam centralizados no Traefik para evitar duplicidade no FastAPI:
- CSP
- X-Frame-Options
- Referrer-Policy
- Permissions-Policy

## OWASP review basico
Revisado e ajustado:
- Upload agora valida extensao e assinatura/MIME real.
- Double extension perigosa e recusada.
- Filename passa por `basename` e sanitizacao.
- CSRF permanece nos forms autenticados.
- Cookies de sessao usam HttpOnly, Secure e SameSite=Strict.
- Login empresa/admin e acompanhamento mantem rate limit.
- Nao ha open redirect nos fluxos de login/logout.

## Backup off-site
`backup.sh` gera backup local criptografado quando `BACKUP_REQUIRE_ENCRYPTION=true`.
Envio B2 permanece configuravel via `rclone` e `BACKBLAZE_BUCKET`; quando ausente, o script avisa sem quebrar o backup local.

## Limpeza operacional
- `retention_cleanup.py` aplica politica de retencao para anexos de denuncias vencidas.
- `cleanup_orphan_uploads.py` remove arquivos sem referencia ativa.
- `cleanup_sessions.py` valida sessoes Redis sem TTL.
- Todos os jobs relevantes possuem dry-run.
