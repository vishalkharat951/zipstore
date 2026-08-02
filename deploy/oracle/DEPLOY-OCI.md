# Migrating ZipStore backend to Oracle Cloud (OCI) — Runbook

Goal: move the Node.js + MongoDB API from **Render** (`zip-backend-myp0.onrender.com`)
to a **free Always Free ARM VM (Ampere A1)** on Oracle Cloud, fronted by nginx
with a free Let's Encrypt TLS cert. The static frontend stays on GitHub Pages.

Architecture after migration:

```
Browser (GitHub Pages frontend)
        │  https://api.yourdomain.com/api/*
        ▼
nginx on OCI VM (TLS, port 443)   ──►  127.0.0.1:5000  ──►  api container
                                                        └──►  mongo container (volume)
```

---

## Step 0 — Prerequisites

- OCI account with a **paid-or-always-free tenancy** (Always Free requires a
  "Pay As You Go" upgrade only if you need more than the free quotas).
- A domain you can add an **A record** to (e.g. `api.yourdomain.com`).
- OCI CLI configured on your laptop (optional; the console UI works too).

---

## Step 1 — Provision the Always Free ARM VM (Ampere A1)

1. OCI Console → **Compute → Instances → Create instance**.
2. Name: `zipstore-api`. Choose compartment.
3. Image: **Ubuntu 24.04** (or **Oracle Linux 8**) — ARM64.
4. Shape: select **Ampere A1 / VM.Standard.A1.Flex**, then choose
   **4 OCPUs / 24 GB RAM** (the Always Free max).
   - If 4/24 is unavailable, use **1 OCPU / 6 GB** — Mongo + Node fit in 6 GB.
5. Networking: select/create a VCN and a public subnet.
6. Add the **VM public SSH key** (your `~/.ssh/id_rsa.pub`).
7. Boot volume: **OCI-optimized storage, 100 GB** (the other 100 GB free block
   is optional for backups).
8. Create. Wait for it to be **Running**. Copy the **Public IP**.

---

## Step 2 — Reserved public IP (so DNS never breaks on reboot)

1. Console → **Networking → IP Management → Reserved Public IPs → Reserve**.
2. Reserve a static IP (e.g. `129.xx.xx.xx`).
3. Instance → **Attached VNICs → Actions → Edit → Assign reserved public IP**.

---

## Step 3 — Security List (ingress rules)

VCN → **Security Lists → Default Security List → Add Ingress Rules**:

| Source | Protocol | Ports | Purpose |
|--------|----------|-------|---------|
| 0.0.0.0/0 | TCP | 22  | SSH |
| 0.0.0.0/0 | TCP | 80  | HTTP (certbot validation) |
| 0.0.0.0/0 | TCP | 443 | HTTPS |

Do **NOT** open 5000/27017 — the API and Mongo stay bound to 127.0.0.1.

---

## Step 4 — DNS

At your DNS provider create:

```
api.yourdomain.com  A  129.xx.xx.xx
```

Wait for propagation (`dig api.yourdomain.com` / `nslookup`).

---

## Step 5 — SSH in and install

```bash
ssh -i ~/.ssh/id_rsa ubuntu@<public-ip>          # Ubuntu image
# or
ssh -i ~/.ssh/id_rsa opc@<public-ip>             # Oracle Linux image
```

Clone the repo and check in:

```bash
sudo apt-get update -y && sudo apt-get install -y git
git clone https://github.com/vishalkharat951/zipstore.git /opt/zipstore
cd /opt/zipstore
```

> If you prefer to copy files instead of cloning, use `rsync -av --exclude
> node_modules --exclude .git ./ ubuntu@<ip>:/opt/zipstore/`.

Prepare the environment (edit the copied file with real values):

```bash
cp deploy/oracle/env.oci.example zipstore-backend/.env
nano zipstore-backend/.env
```

- `JWT_SECRET` → `openssl rand -hex 32`
- `PHONEPE_MERCHANT_ID` / `PHONEPE_SALT_KEY` / `PHONEPE_SALT_INDEX` → your
  real PhonePe merchant credentials (same as used on Render).
- `PHONEPE_CALLBACK_URL=https://api.yourdomain.com/api/payments/phonepe-callback`
- `PHONEPE_ENV=test` until you complete UAT, then `production`.
- `ALLOWED_ORIGINS=https://vishalkharat951.github.io`
- `UPI_ID=<your VPA>`

Run the one-shot provisioning (installs Docker + nginx + certbot, builds and
starts the stack, and issues the TLS cert):

```bash
sudo bash deploy/oracle/setup-oci.sh api.yourdomain.com
```

---

## Step 6 — Migrate the data

Follow **`deploy/oracle/migrate-data.md`** to dump from Atlas and restore into
the OCI Mongo container.

Verify endpoints:

```bash
curl https://api.yourdomain.com/api/health
curl https://api.yourdomain.com/api/products | head -c 300
```

---

## Step 7 — Point the frontend at the new API

Edit **`js/config.js`**:

```js
window.__API_BASE__ = window.__API_BASE__ || 'https://api.yourdomain.com/api';
```

Commit and push to `main`. GitHub Pages serves from the repo root, so the new
`js/config.js` is deployed automatically (clear the Pages cache if stale:
Console → Settings → Pages → Purge, or re-push).

Local smoke test before pushing:

```bash
# from the repo root, serve and open shop.html
python -m http.server 8000
```

---

## Step 8 — PhonePe (if using UPI/gateway)

1. Update the **callback URL** registered with PhonePe to
   `https://api.yourdomain.com/api/payments/phonepe-callback`.
   (Also set it in `zipstore-backend/.env` → `PHONEPE_CALLBACK_URL`.)
2. Do one **UAT test transaction** through the new domain.
3. Only after it succeeds, flip `PHONEPE_ENV=production` and re-deploy.

> The backend now verifies the callback `X-VERIFY` signature and the amount
> before marking an order paid (see `paymentController.js`).

---

## Step 9 — Backups

Add a daily cron on the VM (runs the backup script; keeps 7 dumps):

```bash
sudo crontab -e
30 2 * * * /usr/bin/bash /opt/zipstore/deploy/oracle/backup-mongo.sh >/dev/null 2>&1
```

Copy dumps off the box weekly (e.g. to OCI Object Storage):

```bash
oci os object put -bn <bucket> --name "mongo-$(date +%F).tar.gz" --file /opt/zipstore/backups/mongo-dump-*.tar.gz
```

---

## Step 10 — Update & rollback

Deploy new code:

```bash
sudo bash /opt/zipstore/deploy/oracle/update-app.sh
```

Rollback to a previous dump:

```bash
sudo bash /opt/zipstore/deploy/oracle/restore-mongo.sh /opt/zipstore/backups/mongo-dump-<stamp>.tar.gz
```

---

## Step 11 — Cut over / decommission Render (optional, later)

Only after 24–48h of healthy logs on OCI:

1. Delete the Render web service (or scale it to 0).
2. Optionally retire the Atlas cluster after the final dump.
3. Update `README.md` / `DEPLOYMENT.md` references to the old host.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `curl` to domain fails | Security List missing 443/80, or DNS not propagated. Check `dig api.yourdomain.com`. |
| `Cannot connect to MongoDB` in api logs | `MONGODB_URI` wrong, or mongo container not healthy. `docker compose -f docker-compose.oci.yml -p zipstore ps` |
| API healthy but site 404s on `/api` | `js/config.js` not deployed (old cache), or `__API_BASE__` still `'/api'`. Hard refresh + re-push. |
| PhonePe callback rejected | Domain must be HTTPS and the callback URL exactly matches the one registered with PhonePe. Check nginx logs. |
| `mongo:7` image fails to pull on ARM | Mongo 7 publishes arm64 images; if your region mirrors are flaky, retry or use `mongo:7-jammy`. |
| CORS errors in browser | Ensure `ALLOWED_ORIGINS` includes `https://vishalkharat951.github.io` and `NODE_ENV=production`. |

## No-domain alternative (used on 2026-08-02): OCI API Gateway

You do **not** need to buy a domain. The **OCI API Gateway** (Always Free: 1
gateway + 1M API calls/month) terminates TLS with an Oracle-managed,
browser-trusted certificate and gives you a public HTTPS URL:

```
https://<random>.apigateway.<region>.oci.customer-oci.com/api/*  →  api container
```

How it was set up (all CLI, free tier):

```bash
# 1. Create public gateway on the public subnet (default free cert, no custom domain)
oci api-gateway gateway create \
  --compartment-id <tenancy-ocid> --display-name zipstore-gateway \
  --endpoint-type PUBLIC --subnet-id <public-subnet-ocid>

# 2. Create deployment with one catch-all route.
#    NOTE: wildcard must be a path parameter ({rest*}), NOT /api/*.
#    NOTE: HTTP backend forwards to the EXACT URL; append the wildcard with
#    ${request.path[<param>]} to preserve the request path.
{
  "routes": [{
    "path": "/api/{rest*}",
    "methods": ["ANY"],
    "backend": {
      "type": "HTTP_BACKEND",
      "url": "http://10.0.0.240:5000/api/${request.path[rest]}",
      "connectTimeoutInSeconds": 60, "readTimeoutInSeconds": 60, "sendTimeoutInSeconds": 60
    }
  }]
}
oci api-gateway deployment create --compartment-id <tenancy-ocid> \
  --gateway-id <gateway-ocid> --display-name zipstore-api-deploy \
  --path-prefix "/" --specification file://deployment.json

# 3. Security list: open 443 + 80 from 0.0.0.0/0 (gateway endpoint), and
#    port 5000 ONLY from the VCN CIDR (10.0.0.0/16) so the gateway can reach
#    the VM's private IP. Do NOT open 5000 to the internet.
```

The `docker-compose.oci.yml` in this repo binds the API on `0.0.0.0:5000` for
the gateway (port 5000 remains VCN-internal in the security list).

Current gateway (2026-08-02):
`https://fbecqsp5leqmdfeg23vts53dom.apigateway.ap-mumbai-1.oci.customer-oci.com/api`
— backend VM `zip` private IP `10.0.0.240:5000`.

Session token caveat: `oci session authenticate` sessions expire after ~1 hour
and the written `~/.oci/config` is missing the `user` OCID — re-add it (decode
the token's `sub` claim) or the CLI aborts with "config is invalid".

## Reference

- `docker-compose.oci.yml` — compose stack (api + mongo)
- `deploy/oracle/nginx/zipstore.conf` — nginx TLS reverse proxy
- `deploy/oracle/env.oci.example` — API env template
- `deploy/oracle/setup-oci.sh` — one-shot provisioning
- `deploy/oracle/update-app.sh` — redeploy
- `deploy/oracle/backup-mongo.sh` / `restore-mongo.sh` — backups
- `deploy/oracle/migrate-data.md` — data migration steps
