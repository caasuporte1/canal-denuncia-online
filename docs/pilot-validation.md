# Validação piloto

## Escopo validado
- Homepage do portal em `/`.
- Criação de denúncia pública por tenant.
- Upload com validação reforçada.
- Login empresa e resposta na timeline.
- Acompanhamento pelo denunciante.
- Bloqueio de tenant inativo.
- Isolamento entre tenants.

## Tenants piloto
- `alpha-industria`
- `beta-logistica`
- `gamma-saude`

Criados por `scripts/create_pilot_tenants.py`.

## Procedimento
1. Executar `scripts/create_pilot_tenants.py`.
2. Criar denúncia em cada tenant piloto.
3. Entrar como `tenant_admin` do tenant correspondente.
4. Confirmar que denúncias de outros tenants não aparecem.
5. Responder a denúncia.
6. Acessar `/acompanhar` com protocolo, login e senha.
7. Confirmar que a resposta aparece na timeline do denunciante.
8. Desativar um tenant pelo admin Triton e validar bloqueios.

## Resultado esperado
- Denúncias e respostas ficam isoladas por tenant.
- Acompanhamento de denúncias existentes continua disponível após tenant inativo.
- Nenhum IP, hash ou senha é exposto nas telas.
- Smoke piloto finaliza com `pilot_smoke_test=ok`.

## Validação executada
- `scripts/create_pilot_tenants.py`: tenants piloto presentes e usuários mantidos.
- `scripts/pilot_smoke_test.py`: `pilot_smoke_test=ok` para o tenant `triton`.
- `/health`: `status=ok` com Postgres, Redis e disco `ok`.
