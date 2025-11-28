# Vault Extension E2E Tests

End-to-end tests for the Vault extension using Playwright.

## Prerequisites

- Node.js (v18 or later)
- A deployed Realms instance with the Vault extension
- Test canisters deployed (ckBTC ledger and indexer)

## Setup

1. Install dependencies:
```bash
npm install
npx playwright install chromium
```

## Running Tests

### Local Development

Run all tests:
```bash
./run-e2e-tests.sh
```

Run specific test file:
```bash
./run-e2e-tests.sh specs/vault.spec.ts
```

Run in headed mode (see browser):
```bash
npm run test:headed
```

Run in UI mode (interactive):
```bash
npm run test:ui
```

Debug a specific test:
```bash
npm run test:debug -- specs/vault.spec.ts
```

### CI/CD

The tests are designed to run in GitHub Actions. See the workflow file in `.github/workflows/` for the complete CI setup.

## Test Structure

```
e2e/
├── playwright.config.ts    # Playwright configuration
├── package.json            # NPM dependencies
├── run-e2e-tests.sh       # Test runner script
├── specs/                  # Test specifications
│   └── vault.spec.ts      # Vault extension tests
└── fixtures/               # Test fixtures (if needed)
```

## Test Coverage

The vault E2E tests cover:

- ✅ Vault Manager page display and navigation
- ✅ Vault principal and last refresh timestamp display
- ✅ Transaction history table with pagination
- ✅ Copyable principals and timestamps
- ✅ Page navigation controls
- ✅ Balance information display
- ✅ Transfer form functionality
- ✅ Admin tab information
- ✅ Refresh functionality
- ✅ Human-readable timestamp formatting

## Environment Variables

- `PLAYWRIGHT_BASE_URL` - Base URL for the tests (set automatically by run-e2e-tests.sh)
- `CI` - Set to `true` in CI environment for different behavior (retries, etc.)

## Troubleshooting

### Tests fail with "Could not get realm_frontend canister ID"

Make sure the realm is deployed:
```bash
cd ../../..
realms realm deploy
```

### Browser not found

Install Playwright browsers:
```bash
npx playwright install chromium
```

### Tests timeout

Increase the timeout in `playwright.config.ts` or individual test files.
