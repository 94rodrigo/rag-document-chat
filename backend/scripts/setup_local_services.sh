#!/bin/bash
# Install and configure PostgreSQL 16 + pgvector + Redis natively (Ubuntu 24.04)
# Run with: sudo bash scripts/setup_local_services.sh
set -e

DB_USER="citenest"
DB_PASS="citenest"
DB_NAME="citenest"

echo "==> Installing packages..."
apt-get update -qq
apt-get install -y postgresql-16 postgresql-16-pgvector redis-server

echo "==> Starting services..."
systemctl enable --now postgresql
systemctl enable --now redis-server

echo "==> Creating database user and database..."
sudo -u postgres psql -c "
  DO \$\$
  BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN
      CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';
    END IF;
  END
  \$\$;
"
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || echo "(database already exists)"
sudo -u postgres psql -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || true

echo "==> Verifying pgvector..."
sudo -u postgres psql -d "$DB_NAME" -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"

echo "==> Setting up Redis (bind to localhost only)..."
sed -i 's/^bind .*/bind 127.0.0.1 -::1/' /etc/redis/redis.conf
systemctl restart redis-server

echo ""
echo "✓ PostgreSQL 16 + pgvector running"
echo "✓ Redis 7 running"
echo ""
echo "  DATABASE_URL=postgresql+asyncpg://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME"
echo "  REDIS_URL=redis://localhost:6379/0"
echo ""
echo "To check status:"
echo "  systemctl status postgresql redis-server"
