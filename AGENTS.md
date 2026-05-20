# AGENTS.md

- Não implementar fora da sprint atual.
- Codex só entra na Sprint 0 a partir da Fase D.
- Landing fica fora da VPS em `apps/landing-ddrhost/`.
- Portal na VPS: `denuncia.canaldenunciaonline.com.br`.
- Usar imagens fixas, nunca `latest`.
- Docker Engine fixado em 25.0.5 LTS.
- Não atualizar Docker sem aprovação do Carlos.
- Firewall por Security Group; sem UFW.
- SSH 64022, sem root e sem senha.
