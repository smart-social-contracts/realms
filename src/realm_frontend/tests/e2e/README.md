# E2E Tests

This directory contains end-to-end tests for the Realms frontend application using Playwright.

## Setup

1. Install dependencies:
```bash
npm install
npx playwright install
```

2. Start the development server:
```bash
npm run dev
```

3. Run E2E tests:
```bash
npm run test:e2e
```

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
   - My identities
   - Admin Dashboard
   - Settings
   - Extensions (dropdown with all extensions)
   - Citizen Dashboard
   - Justice Litigation
   - Land Registry
   - AI assistant
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
# Run all E2E tests
npm run test:e2e

# Run with UI mode for debugging
npm run test:e2e:ui

# Run specific test file
npx playwright test specs/navigation.spec.ts

# Run in headed mode to see browser
npx playwright test --headed
```
