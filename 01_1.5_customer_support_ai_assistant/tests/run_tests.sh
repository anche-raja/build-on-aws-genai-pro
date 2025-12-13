#!/bin/bash

# Run Test Suite for Customer Support AI Assistant

set -e

echo "================================"
echo "Customer Support AI Assistant"
echo "Test Suite Runner"
echo "================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to project directory
cd "$(dirname "$0")/.."

echo -e "${YELLOW}Installing test dependencies...${NC}"
pip install -q boto3 pytest pytest-cov

echo ""
echo -e "${YELLOW}Running unit tests...${NC}"
echo "---"

# Run unit tests with coverage
python -m pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

TEST_EXIT_CODE=$?

echo ""
echo "================================"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
echo "================================"
echo ""
echo "Coverage report generated in: htmlcov/index.html"


