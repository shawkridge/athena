#!/bin/bash
# Smoke Tests for Athena HTTP Migration - Phase 4 Docker Stack Verification

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Athena Docker Stack Smoke Tests"
echo "========================================="
echo ""

# Configuration
ATHENA_URL="http://localhost:3000"
DASHBOARD_URL="http://localhost:8000"
ATHENA_TIMEOUT=10
DASHBOARD_TIMEOUT=10

# Helper function to test endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local timeout=$3

    echo -n "Testing $name ... "

    if response=$(curl -s -m $timeout "$url" 2>/dev/null); then
        echo -e "${GREEN}✓ OK${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        return 1
    fi
}

# Track results
TESTS_PASSED=0
TESTS_FAILED=0

echo "Phase 1: Health Checks"
echo "---------------------"

# Test Athena health
if test_endpoint "Athena Health" "$ATHENA_URL/health" $ATHENA_TIMEOUT; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

# Test Dashboard health
if test_endpoint "Dashboard Health" "$DASHBOARD_URL/health" $DASHBOARD_TIMEOUT; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

echo ""
echo "Phase 2: Athena HTTP API Endpoints"
echo "----------------------------------"

# Test Athena key endpoints
athena_endpoints=(
    "/docs"
    "/redoc"
    "/openapi.json"
)

for endpoint in "${athena_endpoints[@]}"; do
    if test_endpoint "Athena $endpoint" "$ATHENA_URL$endpoint" $ATHENA_TIMEOUT; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
done

echo ""
echo "Phase 3: Dashboard API Endpoints"
echo "--------------------------------"

# Test Dashboard key endpoints
dashboard_endpoints=(
    "/docs"
    "/redoc"
    "/openapi.json"
)

for endpoint in "${dashboard_endpoints[@]}"; do
    if test_endpoint "Dashboard $endpoint" "$DASHBOARD_URL$endpoint" $DASHBOARD_TIMEOUT; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
done

echo ""
echo "Phase 4: Memory Operations (via Athena HTTP)"
echo "-------------------------------------------"

# Test core memory operations
memory_endpoints=(
    "/memory/health"
    "/memory/status"
)

for endpoint in "${memory_endpoints[@]}"; do
    if test_endpoint "Memory $endpoint" "$ATHENA_URL$endpoint" $ATHENA_TIMEOUT; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
done

echo ""
echo "========================================="
echo "Test Results Summary"
echo "========================================="
echo "Passed: $TESTS_PASSED"
echo "Failed: $TESTS_FAILED"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Check logs above.${NC}"
    exit 1
fi
