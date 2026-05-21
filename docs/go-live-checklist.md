# Go-live checklist

## Infra
- [x] Docker Engine 25.0.5 LTS fixado.
- [x] Imagens externas sem `latest`.
- [x] Traefik healthy.
- [x] Postgres healthy.
- [x] Redis healthy.
- [x] Portal API healthy.
- [x] TLS válido no domínio do portal.
- [x] DNS do portal operacional.
- [ ] Snapshot VPS feito pelo operador antes do piloto.

## Dados
- [x] Backup manual executado.
- [x] Restore validado.
- [x] Contagem pós-restore validada: `tabelas=8`, `indices=22`, `indices_criticos=4`.
- [ ] Off-site/B2 configurado e testado antes de produção ampla.

## Aplicação
- [x] Homepage `/` funcionando.
- [x] Formulário público funcionando.
- [x] Acompanhamento do denunciante funcionando.
- [x] Painel empresa funcionando.
- [x] Painel admin Triton funcionando.
- [x] Smoke piloto funcionando.
- [x] Upload válido funcionando.
- [x] Upload inválido recusado.
- [x] Cliente inativo bloqueia novo uso e preserva acompanhamento.

## Segurança
- [x] CSRF validado em forms autenticados.
- [x] Cookies seguros validados por configuração.
- [x] Rate limit validado.
- [x] Timing helper validado.
- [x] Cross-tenant validado.
- [x] Headers mantidos no Traefik.

## Operação
- [x] `scripts/ops_summary.sh` executado.
- [x] Logs estruturados ativos.
- [x] Retention cleanup dry-run executado.
- [x] Orphan upload cleanup dry-run executado.
- [x] Documentação operacional criada.
- [x] Troubleshooting documentado.

## Go/no-go
- Go para piloto controlado após snapshot VPS e confirmação do backup off-site.
