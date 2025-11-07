#!/bin/bash

# Phase 5 PostgreSQL Setup Script
# This script sets up everything needed to run Athena with PostgreSQL backend

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "======================================================================"
echo "Athena Phase 5: PostgreSQL Setup"
echo "======================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check Python version
echo -e "${BLUE}[1/6] Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "Found Python $PYTHON_VERSION"

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo "❌ Python 3.10+ required"
    exit 1
fi
echo -e "${GREEN}✓ Python version OK${NC}"
echo ""

# Step 2: Check if venv exists
echo -e "${BLUE}[2/6] Checking virtual environment...${NC}"
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$PROJECT_DIR/.venv"
fi
source "$PROJECT_DIR/.venv/bin/activate"
echo -e "${GREEN}✓ Virtual environment active${NC}"
echo ""

# Step 3: Install dependencies
echo -e "${BLUE}[3/6] Installing dependencies...${NC}"
cd "$PROJECT_DIR"
pip install -e ".[dev]" > /dev/null 2>&1
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Step 4: Check Docker installation
echo -e "${BLUE}[4/6] Checking Docker installation...${NC}"
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose."
    exit 1
fi

echo -e "${GREEN}✓ Docker and Docker Compose found${NC}"
echo ""

# Step 5: Start Docker services
echo -e "${BLUE}[5/6] Starting PostgreSQL and llama.cpp services...${NC}"
docker-compose up -d postgres llamacpp

# Wait for services to be ready
echo "Waiting for services to be healthy..."
for i in {1..30}; do
    if docker-compose exec -T postgres pg_isready -U athena > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ PostgreSQL did not become ready in time"
        exit 1
    fi
    sleep 1
done

echo ""
echo -e "${GREEN}✓ Services started successfully${NC}"
echo ""

# Step 6: Verify imports
echo -e "${BLUE}[6/6] Verifying Python imports...${NC}"
python3 -c "
import sys
sys.path.insert(0, 'src')
from athena.core.database_postgres import PostgresDatabase
from athena.core.database_factory import get_database
print('✓ All imports successful')
"
echo ""

# Summary
echo "======================================================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "======================================================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Verify the database schema:"
echo "   docker-compose exec postgres psql -U athena -d athena \\\"
echo "     SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';"
echo ""
echo "2. Run tests:"
echo "   pytest tests/integration/test_postgres_database.py -v"
echo ""
echo "3. Test PostgreSQL connection in Python:"
echo "   python3 -c \""
echo "   import asyncio"
echo "   from athena.core.database_factory import get_database"
echo "   "
echo "   async def test():"
echo "       db = get_database()"
echo "       await db.initialize()"
echo "       project = await db.create_project('test', '/test/path')"
echo "       print(f'Created project: {project.name}')"
echo "       await db.close()"
echo "   "
echo "   asyncio.run(test())"
echo "   \""
echo ""
echo "4. Stop services:"
echo "   docker-compose down"
echo ""
echo "Docker services:"
echo "  - PostgreSQL: localhost:5432 (athena/athena_dev)"
echo "  - llama.cpp:  localhost:8000 (embeddings)"
echo "  - PgAdmin:    localhost:5050 (optional, use 'docker-compose --profile debug up -d pgadmin')"
echo ""
