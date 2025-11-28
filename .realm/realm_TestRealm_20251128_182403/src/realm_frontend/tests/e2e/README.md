# E2E Tests

This directory contains end-to-end tests for the Realms frontend application using Playwright.

## Setup

1. Install dependencies:
```bash
npm install
npx playwright install
```

2. Deploy the realm (from project root):
```bash
realms realm deploy
```

3. Run E2E tests:

**Option A: Use the convenience script (recommended)**
```bash
./run-e2e-tests.sh
```

**Option B: Set environment variable manually**
```bash
export PLAYWRIGHT_BASE_URL="http://$(dfx canister id realm_frontend).localhost:8000/"
npm run test:e2e
```

**Note:** The `PLAYWRIGHT_BASE_URL` environment variable is required because the canister ID changes with each deployment. The config falls back to `http://localhost:8000/` if not set.

## Test Structure

- `specs/` - Test files
- `fixtures/` - Page object models and test helpers
- `auth-helper.ts` - Authentication utilities
- `sidebar.ts` - Sidebar navigation helpers

## Tests Included

- Authentication flow (Internet Identity creation and admin join)
- Complete sidebar navigation walkthrough
- Individual page load verification

## Video Walkthrough Coverage

These tests reproduce the exact user flow demonstrated in the provided video:

1. **Deployment**: Handled by Playwright's webServer configuration
2. **Internet Identity Creation**: Mocked for reliable testing
3. **Admin Login**: Automated through join form
4. **Sidebar Navigation**: Tests all pages mentioned in video:
   - Dashboard
   - My Identities
   - Admin Dashboard
   - Settings
   - Extensions (dropdown with all extensions)
   - Citizen Dashboard
   - Justice Litigation
   - Land Registry
   - AI assistance
   - Budget Metrics
   - Notifications
   - Public Dashboard
   - test_bench
   - Vault Manager
   - Extensions Marketplace

## Authentication Mocking

Since Internet Identity requires external services, we mock:
- Internet Identity authentication endpoints
- Backend API calls for user status and joining
- Profile management for admin/member roles

## Running Tests

```bash
# Quick run with convenience script (auto-detects canister ID)
./run-e2e-tests.sh

# Run specific test file
./run-e2e-tests.sh specs/workflows.spec.ts

# Or set the base URL manually and use npm scripts
export PLAYWRIGHT_BASE_URL="http://$(dfx canister id realm_frontend).localhost:8000/"
npm run test:e2e

# Run with UI mode for debugging
npm run test:e2e:ui

# Run in headed mode to see browser
npx playwright test --headed
```
