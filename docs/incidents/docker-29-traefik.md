# Incidente: Docker 29 e Traefik

## Sintomas
Traefik iniciava, mas o provider Docker falhava em loop e nenhum router era criado.

## Causa
Docker 29 exigiu API minima mais nova que a API usada pelo SDK Docker embutido no Traefik.

## Correcao
Fixar Docker Engine 25.0.5 LTS via apt e `apt-mark hold`.

## Prevencao
Nao usar `get.docker.com` em producao e nao atualizar Docker sem aprovacao explicita.
