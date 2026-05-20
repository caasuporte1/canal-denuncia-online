# ADR-026 — Docker 25.0.5 LTS

## Status
Aceito — 2026-05-20

## Contexto
Docker 29.5.1 quebrou a compatibilidade com o provider Docker do Traefik por exigir API mínima mais recente que a usada pelo SDK do Traefik.

## Decisão
Usar Docker 25.0.5 LTS fixado via apt e `apt-mark hold`.

## Motivo
Docker 25.0.5 LTS mantém compatibilidade com a API usada pelo Traefik e evita falha do provider Docker.

## Consequências
- Docker não deve ser atualizado sem aprovação explícita.
- Instalação em produção deve fixar versão via apt.
- Não usar `get.docker.com` em produção.
