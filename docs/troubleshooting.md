# Troubleshooting

## Login falhando
- Mensagem esperada para falha: `Usuário ou senha inválidos`.
- Verificar se o usuário está `active`.
- Para empresa, verificar se o tenant está `active`.
- Conferir rate limit de login antes de repetir tentativas.

## Upload recusado
- Extensões aceitas: PDF, JPG, JPEG, PNG, DOCX e XLSX.
- O sistema valida extensão, assinatura/MIME e tamanho.
- Arquivos com dupla extensão são recusados.
- Oriente novo envio com arquivo original válido.

## Redis indisponível
- Sintomas: sessão não persiste, rate limit falha, health acusa Redis.
- Executar `scripts/ops_summary.sh`.
- Conferir logs do container Redis e uso de memória.

## Postgres indisponível
- Sintomas: erro no portal, health acusa Postgres, login não funciona.
- Executar `docker compose ps`.
- Conferir logs do Postgres antes de qualquer restore.

## Rate limit
- Sintoma: HTTP 429 com mensagem genérica.
- Aguardar janela de tempo e evitar tentativas repetidas.
- Se recorrente em piloto, revisar logs por IP e endpoint.

## TLS
- Validar com `curl -fsSL https://denuncia.canaldenunciaonline.com.br/health`.
- Se falhar certificado, revisar logs Traefik e ACME.
- Não usar `-k` em validação final.

## Restore
- Seguir `docs/restore-drill.md`.
- Nunca executar `docker compose down -v`.
- Validar contagem de tabelas após restore.
