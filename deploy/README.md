# Deployment

Lives on a shared droplet (159.223.226.180) alongside two other projects
(`learn-german`, `procurematch`), all behind one Caddy instance. Same
pattern as `procurematch` — see its `docker-compose.yml` comments for the
network-collision reasoning this setup follows.

## One-time server setup

```bash
mkdir -p /opt/reportforge
cd /opt/reportforge
git clone https://github.com/nabeelahmad123/report_forge.git .

# Hand-written, never committed — see backend/.env.example for all keys.
cat > backend/.env <<'EOF'
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-haiku-4-5
REPORT_RATE_LIMIT_PER_MINUTE=10
MAX_LLM_SPEND_USD=5.0
FRONTEND_ORIGIN=https://reportforge.duckdns.org
EOF

docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

Then append `deploy/Caddyfile-snippet` to `/opt/learn-german/Caddyfile` on
the server and reload Caddy (see that file for the exact command) — this
step touches the *shared* Caddy config, so do it by hand rather than
scripting it, and back the file up first.

## Redeploying after a change

```bash
cd /opt/reportforge
git pull
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

## Notes

- Neither container publishes a host port — both join the existing
  `learn-german_default` Docker network (must already exist) and Caddy
  reaches them by container name.
- `mem_limit` on the backend (400m) is a ceiling to contain a runaway on
  this shared 1GB box, not a reservation.
- `/report` is public and unauthenticated; `MAX_LLM_SPEND_USD` (default
  $5, in-memory, resets on container restart) bounds worst-case spend on
  top of the per-IP rate limiter.
