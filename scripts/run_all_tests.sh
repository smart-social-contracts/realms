#!/bin/bash

set -e

echo "Running all tests for PR #17 review..."

echo "1. Running PR #17 regression tests..."
cd /home/ubuntu/realms
python tests/test_pr17_regression.py

echo "2. Running existing extension tests..."
python tests/test_extensions.py

echo "3. Running frontend tests..."
cd src/realm_frontend
npm test

echo "4. Running E2E auth flow tests..."
npm run test:e2e

echo "5. Running E2E login/join tests (requires deployed canisters)..."
cd /home/ubuntu/realms
python tests/e2e_login_join_test.py

echo "All tests completed!"
