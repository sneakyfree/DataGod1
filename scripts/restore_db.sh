#!/usr/bin/env bash
# DataGod Database Restore Script
# Restores from a timestamped backup created by backup_db.sh
#
# Usage:
#   ./scripts/restore_db.sh backups/datagod_20260207_120000.sql.gz
#
# Environment variables:
#   DB_HOST     - PostgreSQL host (default: localhost)
#   DB_PORT     - PostgreSQL port (default: 5432)
#   DB_NAME     - Database name (default: datagod)
#   DB_USER     - Database user (default: datagod)
#   DB_PASSWORD - Database password (required)

set -euo pipefail

# Configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-datagod}"
DB_USER="${DB_USER:-datagod}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 backups/datagod_20260207_120000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo -e "${RED}Error: Backup file not found: ${BACKUP_FILE}${NC}"
    exit 1
fi

echo "=== DataGod Database Restore ==="
echo "From: ${BACKUP_FILE}"
echo "To: ${DB_NAME}@${DB_HOST}:${DB_PORT}"
echo ""
echo -e "${YELLOW}⚠ WARNING: This will DROP and recreate database '${DB_NAME}'${NC}"
read -p "Are you sure? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled."
    exit 0
fi

echo "Dropping existing database..."
PGPASSWORD="${DB_PASSWORD}" dropdb \
    -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" \
    --if-exists "${DB_NAME}" 2>/dev/null || true

echo "Creating fresh database..."
PGPASSWORD="${DB_PASSWORD}" createdb \
    -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" \
    "${DB_NAME}"

echo "Restoring from backup..."
gunzip -c "${BACKUP_FILE}" | PGPASSWORD="${DB_PASSWORD}" pg_restore \
    -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" \
    -d "${DB_NAME}" --no-owner --no-privileges --verbose 2>/dev/null || true

echo -e "${GREEN}✓ Restore completed${NC}"
echo ""
echo "Verify with: psql -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} -c '\\dt'"
