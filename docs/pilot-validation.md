# Validação piloto

## Escopo validado
- Homepage do portal em `/`.
- Criação de denúncia pública por cliente.
- Upload com validação reforçada.
- Login empresa e resposta na timeline.
- Acompanhamento pelo denunciante.
- Bloqueio de cliente inativo.
- Isolamento entre clientes.

## Clientes piloto
- `alpha-industria`
- `beta-logistica`
- `gamma-saude`

Criados por `scripts/create_pilot_tenants.py`.

## Procedimento
1. Executar `scripts/create_pilot_tenants.py`.
2. Criar denúncia em cada cliente piloto.
3. Entrar como `tenant_admin` do cliente correspondente.
4. Confirmar que denúncias de outros clientes não aparecem.
5. Responder a denúncia.
6. Acessar `/acompanhar` com protocolo, login e senha.
7. Confirmar que a resposta aparece na timeline do denunciante.
8. Desativar um cliente pelo admin Triton e validar bloqueios.

## Resultado esperado
- Denúncias e respostas ficam isoladas por cliente.
- Acompanhamento de denúncias existentes continua disponível após cliente inativo.
- Nenhum IP, hash ou senha é exposto nas telas.
- Smoke piloto finaliza com `pilot_smoke_test=ok`.

## Validação executada
- `scripts/create_pilot_tenants.py`: clientes piloto presentes e usuários mantidos.
- `scripts/pilot_smoke_test.py`: `pilot_smoke_test=ok` para o cliente `triton`.
- `/health`: `status=ok` com Postgres, Redis e disco `ok`.
