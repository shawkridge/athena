#!/bin/bash
# Athena Deployment Script (Phase 3)
# Builds, deploys, and verifies Athena stack

set -e

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOCKER_IMAGE_NAME="athena"
DOCKER_IMAGE_TAG="latest"
COMPOSE_FILE="${PROJECT_DIR}/docker/docker-compose.yml"
DEPLOYMENT_TIMEOUT=300  # 5 minutes
LOG_DIR="${PROJECT_DIR}/logs"

# ============================================================================
# Functions
# ============================================================================

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

error() {
    echo -e "${RED}✗ $1${NC}"
}

# ============================================================================
# Pre-flight Checks
# ============================================================================

pre_flight_checks() {
    log "Running pre-flight checks..."

    # Check Docker is installed
    if ! command -v docker &> /dev/null; then
        error "Docker not found. Install from: https://docker.com/products/docker-desktop"
        exit 1
    fi
    success "Docker installed: $(docker --version)"

    # Check Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose not found. Install from: https://docker.com/products/docker-compose"
        exit 1
    fi
    success "Docker Compose installed: $(docker-compose --version)"

    # Check Docker daemon is running
    if ! docker ps &> /dev/null; then
        error "Docker daemon not running. Start Docker Desktop or daemon"
        exit 1
    fi
    success "Docker daemon is running"

    # Check required files exist
    if [ ! -f "$COMPOSE_FILE" ]; then
        error "docker-compose.yml not found at: $COMPOSE_FILE"
        exit 1
    fi
    success "docker-compose.yml found"

    # Create logs directory
    mkdir -p "$LOG_DIR"
    success "Logs directory ready: $LOG_DIR"
}

# ============================================================================
# Build Docker Image
# ============================================================================

build_docker_image() {
    log "Building Docker image..."

    cd "$PROJECT_DIR"

    if docker build -t "${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG}" \
        -f docker/Dockerfile . > "${LOG_DIR}/build.log" 2>&1; then
        success "Docker image built: ${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG}"
    else
        error "Docker build failed. See ${LOG_DIR}/build.log"
        cat "${LOG_DIR}/build.log"
        exit 1
    fi
}

# ============================================================================
# Start Services
# ============================================================================

start_services() {
    log "Starting services with Docker Compose..."

    cd "$PROJECT_DIR"

    if docker-compose -f "$COMPOSE_FILE" up -d > "${LOG_DIR}/compose.log" 2>&1; then
        success "Services started"
    else
        error "Docker Compose failed. See ${LOG_DIR}/compose.log"
        cat "${LOG_DIR}/compose.log"
        exit 1
    fi

    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 5
}

# ============================================================================
# Health Checks
# ============================================================================

health_checks() {
    log "Running health checks..."

    local services=("athena" "prometheus" "grafana")
    local start_time=$(date +%s)
    local timeout=$DEPLOYMENT_TIMEOUT

    for service in "${services[@]}"; do
        log "Checking health of: $service"

        local service_ready=false
        while [ $(( $(date +%s) - start_time )) -lt $timeout ]; do
            if docker-compose -f "$COMPOSE_FILE" ps "$service" | grep -q "Up"; then
                success "$service is running"
                service_ready=true
                break
            fi
            sleep 2
        done

        if [ "$service_ready" = false ]; then
            error "$service failed to start within $timeout seconds"
            log "Container logs:"
            docker-compose -f "$COMPOSE_FILE" logs "$service" | tail -50
            exit 1
        fi
    done

    success "All services are running"
}

# ============================================================================
# Service Verification
# ============================================================================

verify_services() {
    log "Verifying service endpoints..."

    # Athena MCP Server
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        success "Athena MCP server ✓ (http://localhost:8000)"
    else
        warning "Athena MCP server health check failed"
    fi

    # Prometheus
    if curl -sf http://localhost:9090 > /dev/null 2>&1; then
        success "Prometheus ✓ (http://localhost:9090)"
    else
        warning "Prometheus not responding"
    fi

    # Grafana
    if curl -sf http://localhost:3000 > /dev/null 2>&1; then
        success "Grafana ✓ (http://localhost:3000 - admin/admin)"
    else
        warning "Grafana not responding"
    fi
}

# ============================================================================
# Run Tests
# ============================================================================

run_tests() {
    log "Running test suite..."

    cd "$PROJECT_DIR"

    # Run tests inside container
    if docker-compose -f "$COMPOSE_FILE" exec -T athena \
        python -m pytest tests/unit/ tests/integration/ -v --tb=short \
        > "${LOG_DIR}/tests.log" 2>&1; then
        success "Tests passed"
    else
        warning "Some tests failed. See ${LOG_DIR}/tests.log"
        tail -30 "${LOG_DIR}/tests.log"
    fi
}

# ============================================================================
# Summary
# ============================================================================

print_summary() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Athena Deployment Successful!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Services Running:"
    echo -e "  ${GREEN}✓${NC} Athena MCP Server:  ${BLUE}http://localhost:8000${NC}"
    echo -e "  ${GREEN}✓${NC} Prometheus:        ${BLUE}http://localhost:9090${NC}"
    echo -e "  ${GREEN}✓${NC} Grafana:           ${BLUE}http://localhost:3000${NC}"
    echo ""
    echo "Next Steps:"
    echo "  1. Configure Grafana data source (Prometheus: http://prometheus:9090)"
    echo "  2. Import dashboards from dashboard JSON files"
    echo "  3. Set up alerting in Prometheus"
    echo "  4. Monitor logs: tail -f ${LOG_DIR}/*.log"
    echo ""
    echo "Useful Commands:"
    echo "  View logs:        docker-compose -f ${COMPOSE_FILE} logs -f athena"
    echo "  Stop services:    docker-compose -f ${COMPOSE_FILE} down"
    echo "  Remove data:      docker-compose -f ${COMPOSE_FILE} down -v"
    echo ""
    echo "Documentation:"
    echo "  Monitoring:       docs/MONITORING.md"
    echo "  Security:         docs/SECURITY_AUDIT.md"
    echo "  Deployment:       docs/DEPLOYMENT.md"
    echo ""
}

# ============================================================================
# Main
# ============================================================================

main() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     Athena Deployment (Phase 3)        ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""

    pre_flight_checks
    echo ""

    build_docker_image
    echo ""

    start_services
    echo ""

    health_checks
    echo ""

    verify_services
    echo ""

    run_tests
    echo ""

    print_summary
}

# Run main function
main "$@"
