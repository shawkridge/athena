#!/bin/bash
#
# Athena Docker Quick Start Script
# Deploys Athena locally with all required services
#
# Usage:
#   ./docker-up.sh              # Start production services
#   ./docker-up.sh dev          # Start with development tools
#   ./docker-up.sh debug        # Start with debugging (pgadmin, dev-tools)
#   ./docker-up.sh down         # Stop services
#   ./docker-up.sh logs         # View logs
#   ./docker-up.sh clean        # Remove all containers and volumes
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="athena"
ENV_FILE=".env"
DOCKER_COMPOSE_FILE="docker-compose.yml"

# ============================================================================
# Functions
# ============================================================================

print_banner() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                    ATHENA DOCKER LAUNCHER                      ║"
    echo "║           8-Layer Memory System for AI Agents                  ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "${BLUE}➜${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

check_prerequisites() {
    print_step "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        echo "  Download from: https://www.docker.com/products/docker-desktop"
        exit 1
    fi
    print_success "Docker installed"

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed."
        echo "  Download from: https://docs.docker.com/compose/install/"
        exit 1
    fi
    print_success "Docker Compose installed"

    # Check Docker daemon
    if ! docker ps &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    print_success "Docker daemon is running"

    # Check .env file
    if [ ! -f "$ENV_FILE" ]; then
        print_warning ".env file not found. Creating from .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success ".env created from .env.example"
            print_warning "⚠️  Review .env and adjust settings if needed"
        else
            print_error ".env.example not found"
            exit 1
        fi
    else
        print_success ".env file exists"
    fi
}

create_directories() {
    print_step "Creating data directories..."

    mkdir -p ~/.athena/{models,logs}
    mkdir -p ~/.ollama

    print_success "Data directories created"
}

start_services() {
    local profile=$1

    print_step "Starting Athena services..."

    if [ -n "$profile" ]; then
        print_step "Using profile: $profile"
        docker-compose -f $DOCKER_COMPOSE_FILE -f docker-compose.dev.yml \
            --profile "$profile" \
            up -d
    else
        docker-compose -f $DOCKER_COMPOSE_FILE up -d
    fi

    print_success "Services started"
}

wait_for_services() {
    print_step "Waiting for services to become healthy..."

    local max_attempts=60
    local attempt=0

    # Wait for PostgreSQL
    echo -n "  PostgreSQL..."
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose -f $DOCKER_COMPOSE_FILE exec -T postgres pg_isready -U athena &> /dev/null; then
            echo -e " ${GREEN}ready${NC}"
            break
        fi
        echo -n "."
        sleep 1
        ((attempt++))
    done

    if [ $attempt -eq $max_attempts ]; then
        print_error "PostgreSQL failed to start"
        return 1
    fi

    # Wait for Ollama
    echo -n "  Ollama..."
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:11434/api/tags &> /dev/null; then
            echo -e " ${GREEN}ready${NC}"
            break
        fi
        echo -n "."
        sleep 1
        ((attempt++))
    done

    if [ $attempt -eq $max_attempts ]; then
        print_warning "Ollama not ready yet (this is normal on first run, models will be pulled)"
    fi

    # Wait for Athena
    echo -n "  Athena MCP Server..."
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:8000/health &> /dev/null; then
            echo -e " ${GREEN}ready${NC}"
            break
        fi
        echo -n "."
        sleep 1
        ((attempt++))
    done

    if [ $attempt -eq $max_attempts ]; then
        print_warning "Athena not fully initialized (starting, may take 30-60 seconds)"
    fi

    print_success "Services becoming healthy"
}

show_endpoints() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✓ Athena is running!${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Service Endpoints:"
    echo "  Athena MCP Server:    ${BLUE}http://localhost:8000${NC}"
    echo "  Metrics (Prometheus): ${BLUE}http://localhost:9000${NC}"
    echo "  PostgreSQL:           ${BLUE}localhost:5432${NC}"
    echo "  Ollama API:           ${BLUE}http://localhost:11434${NC}"
    echo ""
    echo "Optional Services:"
    echo "  PgAdmin:              ${BLUE}http://localhost:5050${NC} (enable: docker-compose --profile debug up)"
    echo "  Redis:                ${BLUE}localhost:6379${NC} (enable: docker-compose --profile full up)"
    echo ""
    echo "Useful Commands:"
    echo "  View logs:            ${BLUE}docker-compose logs -f${NC}"
    echo "  View specific logs:   ${BLUE}docker-compose logs -f athena${NC}"
    echo "  Check health:         ${BLUE}curl http://localhost:8000/health${NC}"
    echo "  Run tests:            ${BLUE}docker-compose exec athena pytest tests/ -v${NC}"
    echo "  Stop services:        ${BLUE}./docker-up.sh down${NC}"
    echo ""
}

show_help() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  (none)      Start production services"
    echo "  dev         Start with development tools (hot-reload)"
    echo "  debug       Start with debugging tools (pgadmin, dev-tools)"
    echo "  down        Stop all services"
    echo "  logs        View service logs"
    echo "  clean       Remove all containers, volumes, and data"
    echo "  status      Show service status"
    echo "  health      Check service health"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0              # Start production"
    echo "  $0 dev          # Start with development tools"
    echo "  $0 debug        # Start with debugging"
    echo "  $0 logs         # View logs"
    echo "  $0 down         # Stop services"
    echo ""
}

stop_services() {
    print_step "Stopping Athena services..."
    docker-compose -f $DOCKER_COMPOSE_FILE down
    print_success "Services stopped"
}

show_logs() {
    print_step "Showing Athena service logs (Ctrl+C to exit)..."
    docker-compose -f $DOCKER_COMPOSE_FILE logs -f
}

show_status() {
    print_step "Athena service status:"
    docker-compose -f $DOCKER_COMPOSE_FILE ps
}

check_health() {
    print_step "Checking service health..."
    echo ""

    # Check Athena
    echo -n "  Athena MCP Server: "
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        echo -e "${GREEN}✓ Healthy${NC}"
    else
        echo -e "${RED}✗ Unhealthy${NC}"
    fi

    # Check PostgreSQL
    echo -n "  PostgreSQL: "
    if docker-compose -f $DOCKER_COMPOSE_FILE exec -T postgres pg_isready -U athena &> /dev/null; then
        echo -e "${GREEN}✓ Ready${NC}"
    else
        echo -e "${RED}✗ Not Ready${NC}"
    fi

    # Check Ollama
    echo -n "  Ollama: "
    if curl -s http://localhost:11434/api/tags &> /dev/null; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${RED}✗ Not Responding${NC}"
    fi

    echo ""
}

clean_all() {
    print_warning "This will remove all containers, volumes, and data!"
    read -p "Are you sure? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        print_warning "Cancelled"
        return
    fi

    print_step "Removing all Athena services..."
    docker-compose -f $DOCKER_COMPOSE_FILE down -v

    print_step "Removing container volumes..."
    docker volume rm athena-postgres 2>/dev/null || true
    docker volume rm athena-ollama 2>/dev/null || true
    docker volume rm athena-redis 2>/dev/null || true
    docker volume rm athena-logs 2>/dev/null || true

    print_success "All services and data removed"
}

# ============================================================================
# Main
# ============================================================================

print_banner

# Parse command
COMMAND=${1:-start}

case "$COMMAND" in
    start)
        check_prerequisites
        create_directories
        start_services
        wait_for_services
        show_endpoints
        ;;
    dev)
        check_prerequisites
        create_directories
        start_services "debug"
        wait_for_services
        show_endpoints
        echo -e "${YELLOW}Development tools enabled. Hot-reload available.${NC}"
        ;;
    debug)
        check_prerequisites
        create_directories
        start_services "debug"
        wait_for_services
        show_endpoints
        echo -e "${YELLOW}Debug services enabled (pgAdmin, dev-tools).${NC}"
        ;;
    down)
        stop_services
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    health)
        check_health
        ;;
    clean)
        clean_all
        ;;
    help|-h|--help)
        show_help
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        echo ""
        show_help
        exit 1
        ;;
esac
