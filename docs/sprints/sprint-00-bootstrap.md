# Sprint 0 — Bootstrap VPS Portal

## Nota de execução

As Fases A, B e C devem ser executadas por humano. Codex entra a partir da Fase D.

## Domínios

Landing externa DDRHost: `canaldenunciaonline.com.br`  
Portal na VPS: `denuncia.canaldenunciaonline.com.br`

## Ordem obrigatória

A. SSH Hardening — HUMANO  
B. Base operacional da VPS — HUMANO  
C. DNS / Cloudflare — HUMANO  
D. Repositório — Codex  
E. Traefik — Codex  
F. Containers placeholders — Codex  
G. Backup e restore — Codex  
H. Validação final — Codex + humano valida  

## Fase A — SSH Hardening — HUMANO

1. Criar usuário:
```bash
adduser deploy
usermod -aG sudo deploy
```

2. Adicionar chave:
```bash
mkdir -p /home/deploy/.ssh
nano /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
```

3. Editar `/etc/ssh/sshd_config`:
```txt
Port 64022
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
```

4. Validar e reiniciar:
```bash
sshd -t
systemctl restart ssh
```

5. Security Group seguro:
- Adicionar TCP 64022, 80, 443 ANTES de remover ALL.
- Testar `ssh -p 64022 deploy@IP_DA_VPS`.
- Só então remover regra ALL antiga.
- Re-testar SSH.

## Fase B — Base operacional — HUMANO

```bash
sudo apt update && sudo apt upgrade -y
sudo timedatectl set-timezone America/Sao_Paulo
sudo apt install -y ca-certificates curl gnupg git unzip jq fail2ban htop dnsutils netcat-openbsd openssl
```

Fail2ban em `/etc/fail2ban/jail.d/sshd-custom.conf`:
```ini
[sshd]
enabled = true
port = 64022
filter = sshd
logpath = /var/log/auth.log
maxretry = 5
bantime = 1h
findtime = 10m
```

```bash
sudo systemctl restart fail2ban
sudo fail2ban-client status sshd
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker deploy
```

## Fase C — DNS / Cloudflare — HUMANO

Cloudflare DNS-only:
```txt
A denuncia.canaldenunciaonline.com.br -> VPS_IP
```

Validar:
```bash
dig +short denuncia.canaldenunciaonline.com.br
```

## Fases D-H — Codex

- Criar repo em `/opt/canal-denuncia-online`.
- Aplicar arquivos do pacote.
- `cp .env.example .env`
- Preencher `.env`
- `docker compose up -d --build`
- `./scripts/backup.sh`
- `./scripts/restore.sh`
- `./scripts/smoke-test.sh`

## Checklist

- [ ] Fases A/B/C executadas por humano.
- [ ] SSH porta 64022.
- [ ] Fail2ban porta 64022.
- [ ] Security Group sem regra ALL.
- [ ] Cloudflare DNS-only.
- [ ] Healthchecks com start_period 30s.
- [ ] Traefik healthcheck `/ping`.
- [ ] Backup criptografado obrigatório quando flag ativa.
- [ ] Restore valida contagem de tabelas.
- [ ] Smoke test usa VPS_IP.
