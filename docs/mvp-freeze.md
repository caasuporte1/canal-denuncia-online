# MVP freeze — Canal de Denúncia Online

Data: 2026-05-20

## Estado
- MVP v1 pronto para piloto controlado.
- Sprints estáveis: 0, 2, 3, 4, 5, 6 e 7.
- Sprint 8 fecha QA final, go-live controlado e documentação de freeze.

## Stack
- FastAPI, Jinja2, SQLAlchemy e Alembic.
- PostgreSQL 16 Alpine.
- Redis 7 Alpine.
- Traefik v3.3.
- Docker Engine 25.0.5 LTS.
- Python 3.12.

## Funcionalidades congeladas
- Homepage do portal.
- Registro público de denúncia por slug de tenant.
- Denúncia anônima ou identificada.
- Upload com validação e sanitização básica.
- Protocolo, login e senha de acompanhamento.
- PDF de credenciais on-the-fly.
- Acompanhamento pelo denunciante.
- Painel empresa com login, listagem, detalhe, resposta, status e download de anexos.
- Painel Admin Triton com CRUD básico de tenant e visão global.
- Multi-tenant e RBAC.
- Rate limit, CSRF, sessões Redis e timing attack helper.
- Backup, restore drill, ops summary e scripts de limpeza.

## Limitações assumidas
- Sem billing.
- Sem IA.
- Sem dashboard gráfico.
- Sem websocket ou realtime.
- Sem SSO.
- Sem 2FA.
- Sem recuperação de senha.
- Sem onboarding self-service.
- Sem integração externa.
- Sem upload de empresa após criação da denúncia.

## Próximos épicos futuros
- IA assistente V2 para apoio à triagem, sem decisão automatizada.
- Billing e assinatura.
- Onboarding avançado de tenants.
- Recuperação de senha e 2FA.
- Integrações externas conforme demanda do piloto.
- Observabilidade avançada se o volume justificar.

## Critério de mudança pós-freeze
- Correções críticas de segurança e estabilidade podem entrar.
- Novas features devem abrir sprint/épico próprio.
- Mudanças em Docker, Traefik, rede ou arquitetura exigem aprovação explícita.
