#!/bin/bash
# DataGod Deployment Script
# Usage: ./scripts/deploy.sh [environment] [action]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="${1:-development}"
ACTION="${2:-up}"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}DataGod Deployment Script${NC}"
echo "Environment: $ENVIRONMENT"
echo "Action: $ACTION"
echo "----------------------------------------"

# Load environment-specific configuration
load_env() {
    local env_file="$PROJECT_ROOT/.env.$ENVIRONMENT"
    if [ -f "$env_file" ]; then
        echo -e "${GREEN}Loading environment from $env_file${NC}"
        export $(grep -v '^#' "$env_file" | xargs)
    elif [ -f "$PROJECT_ROOT/.env" ]; then
        echo -e "${YELLOW}Using default .env file${NC}"
        export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
    else
        echo -e "${YELLOW}No .env file found, using defaults${NC}"
    fi
}

# Check dependencies
check_dependencies() {
    echo "Checking dependencies..."

    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
        exit 1
    fi

    echo -e "${GREEN}All dependencies are installed.${NC}"
}

# Build images
build() {
    echo "Building Docker images..."
    cd "$PROJECT_ROOT"

    if docker compose version &> /dev/null; then
        docker compose build --no-cache
    else
        docker-compose build --no-cache
    fi

    echo -e "${GREEN}Build completed successfully.${NC}"
}

# Start services
start() {
    echo "Starting services..."
    cd "$PROJECT_ROOT"

    local compose_cmd="docker compose"
    if ! docker compose version &> /dev/null; then
        compose_cmd="docker-compose"
    fi

    if [ "$ENVIRONMENT" = "production" ]; then
        $compose_cmd --profile production up -d
    else
        $compose_cmd up -d
    fi

    echo -e "${GREEN}Services started successfully.${NC}"
    echo ""
    echo "Service URLs:"
    echo "  API:      http://localhost:${API_PORT:-8000}"
    echo "  Frontend: http://localhost:${FRONTEND_PORT:-3000}"
    echo "  Database: localhost:${DB_PORT:-5432}"
    echo "  Redis:    localhost:${REDIS_PORT:-6379}"
}

# Stop services
stop() {
    echo "Stopping services..."
    cd "$PROJECT_ROOT"

    if docker compose version &> /dev/null; then
        docker compose down
    else
        docker-compose down
    fi

    echo -e "${GREEN}Services stopped successfully.${NC}"
}

# Restart services
restart() {
    stop
    start
}

# View logs
logs() {
    local service="${3:-}"
    cd "$PROJECT_ROOT"

    if docker compose version &> /dev/null; then
        docker compose logs -f $service
    else
        docker-compose logs -f $service
    fi
}

# Run database migrations
migrate() {
    echo "Running database migrations..."
    cd "$PROJECT_ROOT"

    if docker compose version &> /dev/null; then
        docker compose exec api alembic upgrade head
    else
        docker-compose exec api alembic upgrade head
    fi

    echo -e "${GREEN}Migrations completed successfully.${NC}"
}

# Seed initial data
seed() {
    echo "Seeding database..."
    cd "$PROJECT_ROOT"

    if docker compose version &> /dev/null; then
        docker compose exec api python -m scripts.seed_jurisdictions
    else
        docker-compose exec api python -m scripts.seed_jurisdictions
    fi

    echo -e "${GREEN}Database seeded successfully.${NC}"
}

# Health check
health() {
    echo "Checking service health..."

    # Check API health
    if curl -s http://localhost:${API_PORT:-8000}/health > /dev/null 2>&1; then
        echo -e "${GREEN}API: Healthy${NC}"
    else
        echo -e "${RED}API: Unhealthy${NC}"
    fi

    # Check Frontend health
    if curl -s http://localhost:${FRONTEND_PORT:-3000} > /dev/null 2>&1; then
        echo -e "${GREEN}Frontend: Healthy${NC}"
    else
        echo -e "${RED}Frontend: Unhealthy${NC}"
    fi

    # Check Database
    if docker compose exec -T db pg_isready > /dev/null 2>&1; then
        echo -e "${GREEN}Database: Healthy${NC}"
    else
        echo -e "${RED}Database: Unhealthy${NC}"
    fi

    # Check Redis
    if docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}Redis: Healthy${NC}"
    else
        echo -e "${RED}Redis: Unhealthy${NC}"
    fi
}

# Cleanup
cleanup() {
    echo "Cleaning up..."
    cd "$PROJECT_ROOT"

    if docker compose version &> /dev/null; then
        docker compose down -v --remove-orphans
        docker system prune -f
    else
        docker-compose down -v --remove-orphans
        docker system prune -f
    fi

    echo -e "${GREEN}Cleanup completed.${NC}"
}

# Backup database
backup() {
    echo "Backing up database..."
    local backup_file="$PROJECT_ROOT/backups/datagod_$(date +%Y%m%d_%H%M%S).sql"
    mkdir -p "$PROJECT_ROOT/backups"

    if docker compose version &> /dev/null; then
        docker compose exec -T db pg_dump -U ${POSTGRES_USER:-datagod} ${POSTGRES_DB:-datagod} > "$backup_file"
    else
        docker-compose exec -T db pg_dump -U ${POSTGRES_USER:-datagod} ${POSTGRES_DB:-datagod} > "$backup_file"
    fi

    gzip "$backup_file"
    echo -e "${GREEN}Backup created: ${backup_file}.gz${NC}"
}

# Show status
status() {
    echo "Service Status:"
    cd "$PROJECT_ROOT"

    if docker compose version &> /dev/null; then
        docker compose ps
    else
        docker-compose ps
    fi
}

# Main execution
main() {
    load_env
    check_dependencies

    case "$ACTION" in
        build)
            build
            ;;
        up|start)
            start
            ;;
        down|stop)
            stop
            ;;
        restart)
            restart
            ;;
        logs)
            logs "$@"
            ;;
        migrate)
            migrate
            ;;
        seed)
            seed
            ;;
        health)
            health
            ;;
        cleanup)
            cleanup
            ;;
        backup)
            backup
            ;;
        status)
            status
            ;;
        deploy)
            build
            start
            migrate
            seed
            health
            ;;
        *)
            echo "Usage: $0 [environment] [action]"
            echo ""
            echo "Environments: development, staging, production"
            echo ""
            echo "Actions:"
            echo "  build    - Build Docker images"
            echo "  up/start - Start all services"
            echo "  down/stop - Stop all services"
            echo "  restart  - Restart all services"
            echo "  logs     - View service logs"
            echo "  migrate  - Run database migrations"
            echo "  seed     - Seed initial data"
            echo "  health   - Check service health"
            echo "  cleanup  - Remove containers and volumes"
            echo "  backup   - Backup database"
            echo "  status   - Show service status"
            echo "  deploy   - Full deployment (build, start, migrate, seed)"
            exit 1
            ;;
    esac
}

main "$@"
