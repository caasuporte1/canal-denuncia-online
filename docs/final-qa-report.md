# Relatório final de QA do MVP

Data: 2026-05-20

## Resultado geral
- Status: aprovado para piloto controlado.
- Containers: `traefik`, `postgres`, `redis` e `portal-api` healthy.
- Health público: `status=ok`, Postgres `ok`, Redis `ok`, disco `ok`.
- Pytest: `49 passed`.
- Smoke piloto: `pilot_smoke_test=ok`.

## Fluxo A — Denunciante
- Homepage `/`: validada com cards de denúncia, acompanhamento e área da empresa.
- Formulário público `/triton`: validado por pytest e smoke piloto.
- Upload: validação de extensão, MIME, tamanho e filename coberta por testes.
- Credenciais: protocolo, login e senha exibidos após criação.
- Acompanhamento `/acompanhar`: login com credenciais e timeline validados.

## Fluxo B — Empresa
- Login em `/auth/login`: validado para `tenant_admin`.
- Listagem e detalhe de denúncias: validados por testes automatizados.
- Resposta da empresa: validada no smoke piloto.
- Alteração de status: validada por testes.
- Download de anexo autorizado e bloqueio cross-tenant: validados por testes.

## Fluxo C — Admin Triton
- Login `admin_triton`: validado por testes.
- Criação de tenant: validada por testes.
- Desativação de tenant: validada por testes.
- Visão global de denúncias: validada por testes.

## Fluxo D — Tenant inativo
- Formulário público bloqueado.
- Login empresa bloqueado.
- Acompanhamento de denúncia existente preservado.
- Cobertura: pytest.

## Fluxo E — Segurança
- Rate limit: coberto por testes.
- Cross-tenant: coberto por testes.
- Sessões Redis: logout, isolamento e expiração cobertos por testes.
- CSRF: forms autenticados cobertos por testes.
- Upload inválido: coberto por testes.

## Operação
- Backup: gerado com sucesso em `backups/canal_denuncia_20260520T234215Z.sql.gz.gpg`.
- Restore drill: `tabelas=8`, `indices=22`, `indices_criticos=4`.
- Retention cleanup dry-run: `attachments=4`, `files=4`.
- Orphan cleanup dry-run: `files=4`.
- Ops summary: Postgres `ok`, Redis `PONG`, disco `/` com 4% em uso.

## Observações
- Integração off-site/B2 não executou nesta rodada porque `rclone/B2` não está configurado.
- Imagem local do `portal-api` aparece como repositório local gerado pelo Compose; imagens externas continuam fixadas.
