# Incidente: parsing do .env

## Sintomas
Scripts operacionais falhavam com erro semelhante a `command not found` ao carregar `.env`.

## Causa
Valor com espacos sem aspas em variavel de ambiente.

## Correcao
Colocar valores com espacos entre aspas duplas.

## Prevencao
Revisar `.env.example` e manter valores textuais com espacos sempre entre aspas.
