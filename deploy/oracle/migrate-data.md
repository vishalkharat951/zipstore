# Data migration: Render/Atlas -> Oracle Cloud MongoDB

The live Node API on Render uses a **MongoDB Atlas** cluster
(`MONGODB_URI=mongodb+srv://zipstore_admin:...@cluster0.xxx.mongodb.net/zipstore`).
This guide moves that data to the MongoDB container on the OCI VM.

## 1. Export from the current database

Run this **on any machine with the MongoDB shell tools** (or inside the
current Render/Atlas setup). Install tools first if needed:

```bash
# Ubuntu/Debian
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg
echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt-get update && sudo apt-get install -y mongodb-database-tools

# or just download the tarball for your OS:
# https://www.mongodb.com/try/download/database-tools
```

Dump the whole `zipstore` database to a single archive:

```bash
mongodump --uri "mongodb+srv://zipstore_admin:YOUR_PASSWORD@cluster0.xxx.mongodb.net/zipstore" \
  --archive=mongo-dump.zipstore.gz --gzip
```

Copy the archive to the OCI VM:

```bash
scp -i ~/.ssh/your_key mongo-dump.zipstore.gz opc@<vm-public-ip>:/tmp/
```

## 2. Import into the OCI MongoDB container

```bash
sudo bash /path/to/repo/deploy/oracle/restore-mongo.sh /tmp/mongo-dump.zipstore.gz
```

Verify:

```bash
docker compose -f /path/to/repo/docker-compose.oci.yml -p zipstore exec mongo \
  mongosh zipstore --quiet --eval "printjson({ products: db.products.countDocuments(), categories: db.categories.countDocuments(), users: db.users.countDocuments(), orders: db.orders.countDocuments() })"
```

## 3. Check your new .env matches the migrated data

- `MONGODB_URI=mongodb://mongo:27017/zipstore` (compose network name)
- Database name `zipstore` must match what you dumped.

## 4. Cut over

Once verified, update the frontend (`js/config.js`) and PhonePe callback
(see `DEPLOY-OCI.md`), then decommission Render.

> Tip: keep the Atlas cluster and the Render app running (but stop traffic)
> until you have 24–48h of clean logs on OCI. This gives a safe rollback path.
