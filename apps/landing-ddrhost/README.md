# Landing Page — Canal de Denúncia Online

Landing comercial hospedada no DDRHost (fora da VPS).

## Domínio destino

```
canaldenunciaonline.com.br
```

## Tecnologia

- HTML estático puro
- Tailwind via CDN (sem build, sem Node)
- CSS complementar próprio em `style.css`
- Sem JavaScript de framework

## Como publicar no DDRHost

Quando o sócio contratar o plano DDRHost:

1. Acessar o painel de controle do DDRHost (cPanel ou similar)
2. Abrir o gerenciador de arquivos OU conectar via FTP
3. Navegar até a pasta `public_html/` (ou raiz do domínio)
4. Fazer upload de:
   - `index.html`
   - `style.css`
5. Confirmar acesso em `https://canaldenunciaonline.com.br`

## Pendências de conteúdo

Antes de divulgar publicamente, completar:

- [ ] CNPJ Triton (rodapé)
- [ ] Endereço Triton (rodapé)
- [ ] Logo oficial (substituir o placeholder "T" no header e footer)
- [ ] Política de Privacidade (criar página separada)
- [ ] Termos de Uso (criar página separada)
- [ ] Validar número WhatsApp (atualmente: 21 98272-4974)

## Estrutura

```
apps/landing-ddrhost/
├── index.html      # Página principal
├── style.css       # CSS complementar
└── README.md       # Este arquivo
```

## Notas

- Esta pasta NÃO sobe na VPS via Docker.
- Upload manual para DDRHost por FTP/painel.
- Links da landing apontam para `https://denuncia.canaldenunciaonline.com.br` (portal na VPS).
