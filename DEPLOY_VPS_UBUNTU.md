# Deploy Guide (Ubuntu VPS + Domain)

This guide is for this repository and Ubuntu VPS `95.163.226.242`.

## 1. Current server state

Based on your console output:

- `apt update/upgrade` completed successfully.
- Docker Engine and `docker compose` plugin are installed and running.
- `docker version` is healthy.

Only one important action is still pending:

- A new kernel was installed (`6.8.0-100`), but the server is still running the old one (`6.8.0-85`).

Run:

```bash
reboot
```

Reconnect and verify:

```bash
ssh root@95.163.226.242
uname -r
docker version
docker compose version
```

Expected kernel: `6.8.0-100-generic` (or newer).

## 2. Firewall

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw status
```

## 3. Clone project

```bash
mkdir -p /opt
cd /opt
git clone https://github.com/Querser/Project-for-Elmir.git
cd Project-for-Elmir
git checkout main
```

## 4. Create production env file

```bash
cp .env.prod.example .env.prod
nano .env.prod
```

Fill required values:

- `DOMAIN`
- `POSTGRES_PASSWORD`
- `DATABASE_URL` (must match DB credentials)
- `ADMIN_PASSWORD`
- `ADMIN_TOKEN_SECRET` (long random secret)
- Telegram variables (`TELEGRAM_BOT_TOKEN`, webhook URLs, secret)

## 5. Start production stack

```bash
cd /opt/Project-for-Elmir/infra
docker compose --env-file ../.env.prod -f docker-compose.prod.yml up -d --build
```

## 6. Check service health

```bash
docker compose --env-file ../.env.prod -f docker-compose.prod.yml ps
docker compose --env-file ../.env.prod -f docker-compose.prod.yml logs -f --tail=200
```

Quick checks:

```bash
curl -I http://95.163.226.242/
curl -I http://95.163.226.242/admin/
curl http://95.163.226.242/health
```

## 7. Domain setup

Create DNS records at your registrar:

- `A` record: `previewsite-nikolaev.online` -> `95.163.226.242`
- Optional `A` record: `www.previewsite-nikolaev.online` -> `95.163.226.242`

When DNS is propagated, Caddy will issue TLS certificate automatically.

Check:

```bash
curl -I https://previewsite-nikolaev.online/
curl -I https://previewsite-nikolaev.online/admin/
curl https://previewsite-nikolaev.online/health
```

## 8. Telegram webhook

After HTTPS is active, ensure these values in `.env.prod`:

- `TELEGRAM_WEBAPP_URL=https://previewsite-nikolaev.online/`
- `TELEGRAM_ADMIN_WEBAPP_URL=https://previewsite-nikolaev.online/admin/`
- `TELEGRAM_WEBHOOK_URL=https://previewsite-nikolaev.online/api/v1/telegram/webhook`

Restart backend after changes:

```bash
cd /opt/Project-for-Elmir/infra
docker compose --env-file ../.env.prod -f docker-compose.prod.yml up -d backend
```

## 9. Update deployment

```bash
cd /opt/Project-for-Elmir
git pull origin main
cd infra
docker compose --env-file ../.env.prod -f docker-compose.prod.yml up -d --build
```

## 10. Rollback (if needed)

```bash
cd /opt/Project-for-Elmir
git log --oneline -n 10
git checkout <old_commit_hash>
cd infra
docker compose --env-file ../.env.prod -f docker-compose.prod.yml up -d --build
```

## 11. Useful commands

```bash
# All logs
cd /opt/Project-for-Elmir
docker compose --env-file .env.prod -f infra/docker-compose.prod.yml logs -f

# Backend logs only
docker compose --env-file .env.prod -f infra/docker-compose.prod.yml logs -f backend

# Restart one service
docker compose --env-file .env.prod -f infra/docker-compose.prod.yml restart backend
```

## 12. Security checklist

- Do not use `.env.dev` on VPS.
- Keep `ALLOW_INSECURE_HEADER_AUTH=0`.
- Keep `DEV_AUTO_CREATE_USER_FROM_HEADER=0`.
- Rotate leaked Telegram/admin secrets before production use.
