# Checklist operacional

## Rotina diária
- Verificar `/health` e confirmar `status=ok`.
- Executar `scripts/ops_summary.sh` e revisar containers, Postgres, Redis, disco, uploads e backups.
- Confirmar se o TLS do portal responde sem `-k`.
- Revisar tentativas de login falhas e eventos de rate limit nos logs.

## Criar tenant
- Acessar `/auth/login` com usuário `admin_triton`.
- Entrar em `/admin/tenants/novo`.
- Informar nome, documento, slug em lowercase e e-mail do admin inicial.
- Entregar a senha temporária exibida uma única vez por canal seguro.

## Validar tenant
- Abrir `/{slug}` e criar denúncia teste.
- Acessar `/auth/login` com o admin do tenant.
- Confirmar que a denúncia aparece apenas para o tenant correto.
- Responder a denúncia e validar em `/acompanhar`.

## Desativar tenant
- Acessar detalhe do tenant em `/admin/tenants/{id}`.
- Alterar status para `inactive`.
- Confirmar que `/{slug}` e login da empresa ficam bloqueados.
- Confirmar que `/acompanhar` continua funcionando para denúncias já criadas.

## Backup e restore
- Executar `scripts/backup.sh`.
- Executar `scripts/restore.sh` em janela controlada.
- Conferir `docs/restore-drill.md` antes de restore emergencial.
- Manter cópia off-site conforme política vigente.

## Uploads
- Criar denúncia teste com PDF e imagem.
- Confirmar que anexos aparecem no painel empresa.
- Recusar arquivo inválido antes de avançar piloto.

## Incidente
- Consultar `docs/troubleshooting.md`.
- Registrar sintomas, horário, impacto, correção e prevenção em `docs/incidents/`.
