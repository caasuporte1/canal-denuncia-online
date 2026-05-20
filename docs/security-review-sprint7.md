# Security review Sprint 7

## Cookies e sessão
- Sessões de empresa/admin continuam em Redis com cookie `HttpOnly`, `Secure` e `SameSite=Strict`.
- Sessões do denunciante permanecem separadas e com TTL curto.
- Logout invalida a sessão no Redis.

## CSRF
- Forms autenticados de empresa, admin e acompanhamento mantêm CSRF.
- Login público continua protegido por rate limit e mensagem genérica.

## Headers
- Security headers permanecem centralizados no Traefik.
- FastAPI não duplica CSP, HSTS, X-Frame-Options, Referrer-Policy ou Permissions-Policy.

## Rate limits
- Login empresa/admin: mantido em `5/min`.
- Acompanhamento do denunciante: mantido em `5/min`.
- Formulário público e PDF de credenciais preservam limites da Sprint 2.

## Tenant isolation
- Rotas empresa seguem `require_auth()` e filtram por `tenant_id`.
- Admin Triton exige role `admin_triton`.
- Tenant inativo bloqueia formulário público e login empresa, preservando acompanhamento histórico.

## Timing attack
- Acompanhamento usa `verify_credentials_constant_time()`.
- Credenciais inválidas retornam mensagem única e não revelam qual campo falhou.

## Uploads
- Validação reforçada por extensão, MIME sniffing, dupla extensão, tamanho e sanitização.
- Arquivos são salvos fora de diretório público.

## Pontos residuais para piloto
- Monitorar volume de 429 para ajustar limites sem reduzir proteção.
- Continuar restore drill periódico antes de entrada de cliente real.
