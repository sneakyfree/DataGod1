#!/usr/bin/env bash
# DataGod Database Backup Script
# Creates timestamped pg_dump backups with optional S3 upload
#
# Usage:
#   ./scripts/backup_db.sh                    # Basic backup
#   ./scripts/backup_db.sh --upload-s3       # Backup + upload to S3
#
# Environment variables:
#   DB_HOST       - PostgreSQL host (default: localhost)
#   DB_PORT       - PostgreSQL port (default: 5432)
#   DB_NAME       - Database name (default: datagod)
#   DB_USER       - Database user (default: datagod)
#   DB_PASSWORD   - Database password (required)
#   BACKUP_DIR    - Backup directory (default: ./backups)
#   S3_BUCKET     - S3 bucket for remote backup
#   RETENTION_DAYS - Days to keep local backups (default: 30)

set -euo pipefail

# Configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-datagod}"
DB_USER="${DB_USER:-datagod}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "=== DataGod Database Backup ==="
echo "Database: ${DB_NAME}@${DB_HOST}:${DB_PORT}"
echo "Backup to: ${BACKUP_FILE}"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Perform backup
echo "Starting backup..."
PGPASSWORD="${DB_PASSWORD}" pg_dump \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --format=custom \
    --compress=9 \
    --verbose \
    2>/dev/null | gzip > "${BACKUP_FILE}"

# Verify backup
if [ -f "${BACKUP_FILE}" ] && [ -s "${BACKUP_FILE}" ]; then
    SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo -e "${GREEN}✓ Backup successful: ${BACKUP_FILE} (${SIZE})${NC}"
else
    echo -e "${RED}✗ Backup failed!${NC}"
    exit 1
fi

# Upload to S3 if requested
if [ "${1:-}" = "--upload-s3" ] && [ -n "${S3_BUCKET:-}" ]; then
    echo "Uploading to S3: s3://${S3_BUCKET}/backups/"
    aws s3 cp "${BACKUP_FILE}" "s3://${S3_BUCKET}/backups/"
    echo -e "${GREEN}✓ S3 upload successful${NC}"
fi

# Clean up old backups
echo "Cleaning up backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "${DB_NAME}_*.sql.gz" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true

REMAINING=$(find "${BACKUP_DIR}" -name "*.sql.gz" | wc -l)
echo "Local backups remaining: ${REMAINING}"
echo -e "${GREEN}=== Backup complete ===${NC}"
