# Go-live security review

Data: 2026-05-20

## Resultado
- Status: aprovado para piloto controlado.
- Nenhuma mudança arquitetural necessária.
- Security headers permanecem centralizados no Traefik.

## CSP e headers
- CSP, HSTS, X-Frame-Options, Referrer-Policy e Permissions-Policy seguem no middleware Traefik.
- FastAPI não duplica security headers.
- TLS validado via `/health` público sem `-k`.

## CSRF
- Forms autenticados de empresa, admin e denunciante mantêm CSRF.
- Testes cobrem logout, alteração de status, resposta e rotas administrativas.

## Cookies e sessões
- Cookies de sessão usam `HttpOnly`, `Secure` e `SameSite=Strict`.
- Sessão empresa/admin e sessão denunciante são separadas.
- Sessão do denunciante mantém TTL curto.
- Logout invalida sessão.

## Rate limits
- Login empresa/admin: `5/min`.
- Login denunciante: `5/min`.
- Formulário público e PDF de credenciais mantêm limites já implementados.
- Resposta 429 segue genérica.

## Timing helper
- Acompanhamento usa `verify_credentials_constant_time()`.
- Credenciais inválidas retornam mensagem única.
- Dummy hash coberto por teste automatizado.

## Uploads
- Validação por extensão permitida, double extension, MIME sniffing, tamanho e sanitização.
- Arquivos ficam fora de diretório público.
- Testes cobrem MIME spoof, extensão inválida e filename traversal.

## RBAC e multi-tenant
- Empresa acessa apenas o próprio tenant.
- Admin Triton exige role `admin_triton`.
- Cross-tenant de denúncia, status, resposta e anexo é bloqueado por testes.

## Audit logs
- Eventos críticos existem para login, logout, denúncia, resposta, status, download, admin e acessos do denunciante.
- Não registrar senha, hashes, IP do denunciante em telas públicas ou templates.

## Pendências controladas
- Configurar off-site/B2 antes de produção ampla.
- Monitorar volume de rate limit durante piloto para ajuste operacional.
