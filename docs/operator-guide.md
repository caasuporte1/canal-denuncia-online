# Guia do operador Triton

## Acessar o admin
1. Abra `https://denuncia.canaldenunciaonline.com.br/auth/login`.
2. Entre com o usuário admin Triton.
3. Use `/admin` para visão geral, clientes e denúncias globais.

## Criar cliente
1. Acesse `/admin/tenants/novo`.
2. Cadastre razão social/nome, CNPJ, dados de contato, responsável pelo tratamento de denúncias, admin inicial e link do portal.
3. Copie a senha temporária exibida uma única vez.
4. Envie credenciais ao responsável por canal seguro.

## Criar denúncia teste
1. Acesse `https://denuncia.canaldenunciaonline.com.br/{link-do-portal}`.
2. Envie uma denúncia anônima com categoria `Outros`.
3. Guarde protocolo, login e senha.

## Responder denúncia
1. Entre como usuário da empresa em `/auth/login`.
2. Abra `/empresa/denuncias`.
3. Acesse o detalhe, revise dados e anexos.
4. Registre resposta objetiva, sem expor dados desnecessários.

## Acompanhar como denunciante
1. Acesse `/acompanhar`.
2. Informe protocolo, login e senha.
3. Confira status e respostas da empresa.

## Troubleshooting rápido
- Login falhando: valide usuário ativo, cliente ativo e rate limit.
- Upload recusado: confirme extensão, MIME real e tamanho.
- Canal não encontrado: confirme link do portal e status do cliente.
- Lentidão: rode `scripts/ops_summary.sh` e veja Postgres, Redis, disco e containers.
