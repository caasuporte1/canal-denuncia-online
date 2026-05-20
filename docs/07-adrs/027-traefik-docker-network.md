# ADR-027 — traefik.docker.network em serviços multi-rede

## Status
Aceito — 2026-05-20

## Contexto
Serviços expostos pelo Traefik podem estar conectados a mais de uma rede Docker. Quando isso ocorre, o Traefik pode escolher um IP de uma rede que ele não acessa.

## Decisão
Serviços expostos pelo Traefik e conectados a múltiplas redes devem declarar:

```yaml
- "traefik.docker.network=cdo-web"
```

## Motivo
Evitar que o Traefik escolha o IP da rede `internal`, o que gera timeout e resposta `504 Gateway Timeout`.

## Consequências
- Todo serviço multi-rede publicado pelo Traefik deve apontar explicitamente para `cdo-web`.
- Serviços internos sem exposição pública não precisam dessa label.
