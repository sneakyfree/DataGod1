#!/usr/bin/env bash
# =============================================================================
# DataGod SSL/TLS Certificate Initialization
# Uses Let's Encrypt (certbot) to obtain and configure SSL certificates.
#
# Usage:
#   ./scripts/init-ssl.sh yourdomain.com [your@email.com]
#
# Prerequisites:
#   - Docker and docker-compose installed
#   - Domain DNS pointing to this server's IP
#   - Port 80 accessible from the internet
# =============================================================================

set -euo pipefail

DOMAIN="${1:?Usage: $0 <domain> [email]}"
EMAIL="${2:-admin@${DOMAIN}}"
COMPOSE_FILE="${3:-docker-compose.prod.yml}"
DATA_PATH="./certbot"
NGINX_SSL_CONF="./nginx/nginx.ssl.conf"

echo "╔══════════════════════════════════════════════════╗"
echo "║  DataGod SSL/TLS Certificate Setup               ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║  Domain: ${DOMAIN}"
echo "║  Email:  ${EMAIL}"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# --- Step 1: Create required directories ---
echo "[1/5] Creating certificate directories..."
mkdir -p "${DATA_PATH}/conf"
mkdir -p "${DATA_PATH}/www"

# --- Step 2: Generate temporary self-signed cert for nginx to start ---
echo "[2/5] Generating temporary self-signed certificate..."
CERT_DIR="${DATA_PATH}/conf/live/${DOMAIN}"
mkdir -p "${CERT_DIR}"

if [ ! -f "${CERT_DIR}/fullchain.pem" ]; then
    openssl req -x509 -nodes -newkey rsa:2048 \
        -days 1 \
        -keyout "${CERT_DIR}/privkey.pem" \
        -out "${CERT_DIR}/fullchain.pem" \
        -subj "/CN=${DOMAIN}" \
        2>/dev/null
    echo "   ✓ Temporary certificate created"
else
    echo "   ✓ Certificate already exists, skipping"
fi

# --- Step 3: Update nginx config with actual domain ---
echo "[3/5] Updating nginx SSL config with domain: ${DOMAIN}..."
if [ -f "${NGINX_SSL_CONF}" ]; then
    sed -i "s/\${DOMAIN:-localhost}/${DOMAIN}/g" "${NGINX_SSL_CONF}"
    sed -i "s/server_name _;/server_name ${DOMAIN} www.${DOMAIN};/g" "${NGINX_SSL_CONF}"
    echo "   ✓ nginx.ssl.conf updated"
fi

# --- Step 4: Start nginx with temporary cert ---
echo "[4/5] Starting nginx..."
docker-compose -f "${COMPOSE_FILE}" up -d nginx
sleep 3

# --- Step 5: Obtain real Let's Encrypt certificate ---
echo "[5/5] Requesting Let's Encrypt certificate..."
docker-compose -f "${COMPOSE_FILE}" run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "${EMAIL}" \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d "${DOMAIN}" \
    -d "www.${DOMAIN}"

# --- Reload nginx with real cert ---
echo ""
echo "Reloading nginx with production certificate..."
docker-compose -f "${COMPOSE_FILE}" exec nginx nginx -s reload

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  ✓ SSL/TLS setup complete!                       ║"
echo "║                                                  ║"
echo "║  https://${DOMAIN} is now secured."
echo "║                                                  ║"
echo "║  Certbot auto-renewal is running via the         ║"
echo "║  certbot container in docker-compose.prod.yml.   ║"
echo "╚══════════════════════════════════════════════════╝"
