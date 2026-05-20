# Incidente: Traefik em servico multi-rede

## Sintomas
HTTPS e certificado funcionavam, mas `/health` retornava 504.

## Causa
Traefik escolheu o IP da rede `internal` do container da API, inacessivel a partir da rede web.

## Correcao
Adicionar `traefik.docker.network=cdo-web` ao servico publicado.

## Prevencao
Todo servico multi-rede exposto pelo Traefik deve declarar explicitamente a rede Docker publica.
