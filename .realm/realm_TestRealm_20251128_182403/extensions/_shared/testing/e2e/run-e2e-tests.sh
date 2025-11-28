#!/usr/bin/env bash

# Shared E2E Test Runner for Realms Extensions
# Runs Playwright browser tests with proper setup
#
# Usage: ./run-e2e-tests.sh [PLAYWRIGHT_OPTIONS]
# Example: ./run-e2e-tests.sh --headed
# Example: ./run-e2e-tests.sh --debug

set -e

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Default environment variables
export PLAYWRIGHT_BASE_URL=${PLAYWRIGHT_BASE_URL:-"http://localhost:8000"}

echo -e "${BLUE}🎭 Realms Extension E2E Test Runner${NC}"
echo ""
echo "Base URL: $PLAYWRIGHT_BASE_URL"
echo ""

# Ensure dependencies are installed
if [ ! -d "$SCRIPT_DIR/node_modules" ]; then
  echo -e "${BLUE}📦 Installing npm dependencies...${NC}"
  cd "$SCRIPT_DIR"
  npm install
  echo ""
fi

# Ensure Playwright browsers are installed (pinned to version in package.json)
# This handles cases where npm install updates Playwright or Docker image browsers are missing
PLAYWRIGHT_CACHE="${HOME}/.cache/ms-playwright"

# In Docker environments, always ensure browsers are installed
if [ -f /.dockerenv ]; then
  echo "🐳 Docker environment detected - ensuring browsers are installed..."
  cd "$SCRIPT_DIR"
  npx playwright install chromium --with-deps || npx playwright install chromium
  echo ""
else
  # For local development, check if browsers exist
  if ! ls "${PLAYWRIGHT_CACHE}"/chromium* > /dev/null 2>&1; then
    echo -e "${BLUE}📥 Installing Playwright browsers...${NC}"
    cd "$SCRIPT_DIR"
    npx playwright install chromium
    echo ""
  else
    echo -e "${GREEN}✅ Playwright browsers already installed${NC}"
    echo ""
  fi
fi

# Warm up the extension page before running tests (if URL is available)
if [ -n "${E2E_WARMUP_PATH:-}" ]; then
  echo -e "${YELLOW}🔥 Warming up extension page...${NC}"
  curl -s "${PLAYWRIGHT_BASE_URL}${E2E_WARMUP_PATH}" > /dev/null || echo "⚠️  Warmup request failed (may still work)"
  sleep 3
  echo -e "${GREEN}✅ Warmup complete${NC}"
  echo ""
fi

echo -e "${BLUE}🎭 Running E2E tests...${NC}"
echo ""

cd "$SCRIPT_DIR"

# Run Playwright with all passed arguments
npx playwright test "$@"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  echo ""
  echo -e "${GREEN}✅ E2E tests passed!${NC}"
else
  echo ""
  echo -e "${YELLOW}⚠️  E2E tests failed${NC}"
  echo -e "${BLUE}💡 View the HTML report:${NC} npx playwright show-report"
fi

exit $EXIT_CODE
