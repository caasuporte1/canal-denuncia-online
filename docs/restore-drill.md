# Restore drill

## Objetivo
Validar que o backup PostgreSQL criptografado pode ser restaurado em banco temporario sem afetar o banco principal.

## Procedimento
1. Gerar backup com `./scripts/backup.sh`.
2. Executar `./scripts/restore.sh`.
3. Conferir o relatorio final com contagem de tabelas, indices e indices criticos.

## Validacoes
- Contagem de tabelas do restore deve bater com a origem.
- Contagem de indices do restore deve bater com a origem.
- Indices criticos de reports, attachments, audit logs e email_notifications devem existir.

## Backup off-site
O script `backup.sh` mantém criptografia local obrigatoria quando `BACKUP_REQUIRE_ENCRYPTION=true`.
Quando `rclone` e `BACKBLAZE_BUCKET` estiverem configurados, o artefato criptografado e copiado para B2.
Retencao esperada: 7 dias local e 30 dias off-site conforme configuracao operacional.
