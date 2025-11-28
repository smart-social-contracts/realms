# Payment Accounts E2E Tests

## Overview

Comprehensive Playwright end-to-end tests for the Payment Accounts functionality in the Member Dashboard extension.

## Test Coverage

### Core Functionality Tests

1. **Display Tests**
   - Payment Accounts section visibility
   - "Add Payment Account" button presence
   - Empty state handling

2. **Modal Interaction Tests**
   - Opening the Add Payment Account modal
   - Modal form field validation
   - Closing modal with Cancel button

3. **Form Validation Tests**
   - Required field validation (label, address)
   - ICP address format validation
   - Network-specific address validation

4. **Account Management Tests**
   - Successfully adding an ICP payment account
   - Displaying account details (label, network, currency, address, timestamp)
   - Removing payment accounts
   - Confirmation dialog on removal

5. **Network & Currency Tests**
   - Multiple network support (ICP, Bitcoin, Ethereum, SEPA)
   - Dynamic currency options based on network selection
   - Proper network badge display

6. **Data Persistence Tests**
   - Account appears in list after creation
   - Created timestamp display
   - Account removal from list

7. **UI/UX Tests**
   - Loading states while fetching accounts
   - Empty state messaging
   - Error message display

## Test Files

- **Location**: `/extensions/member_dashboard/tests/e2e/specs/member_dashboard.spec.ts`
- **Test Suite**: "Payment Accounts Functionality Tests"
- **Number of Tests**: 14 comprehensive test cases

## Running the Tests

### Option 1: Docker-Based Tests (Recommended)

The extension uses a shared Docker-based testing framework that includes Playwright and browsers pre-installed.

**Run all tests (Python + Playwright E2E)**:
```bash
cd extensions/member_dashboard
./run_tests.sh
```

This will:
- Pull the Realms test Docker image (browsers already installed)
- Set up a test environment
- Run Python tests
- Run Playwright E2E tests
- Collect test results and logs

**Benefits**:
- ✅ No need to install browsers locally
- ✅ Consistent test environment
- ✅ Same setup used in CI/CD
- ✅ Includes full Realms backend

### Option 2: Local Development Tests

For rapid iteration during development, you can run tests locally.

**Prerequisites**:
1. Start the local development environment:
   ```bash
   dfx start --clean --background
   dfx deploy
   ```

2. Install test dependencies (one time):
   ```bash
   cd extensions/member_dashboard/tests/e2e
   npm install
   npx playwright install chromium
   ```

**Run Tests Locally**:

```bash
cd extensions/member_dashboard/tests/e2e

# All tests (headless)
npm test

# With browser UI (headed mode)
npm run test:headed

# Debug mode (step through tests)
npm run test:debug

# Interactive UI mode
npm run test:ui

# Run only Payment Accounts tests
npx playwright test --grep "Payment Accounts"
```

**Note**: Local tests require a running dfx instance with deployed canisters.

## Test Scenarios

### 1. Adding a Payment Account

Tests the complete flow of adding a new payment account:
- Opens modal
- Fills in form fields (label, network, currency, address)
- Validates ICP address format
- Submits form
- Verifies account appears in list

### 2. Validation Errors

Tests various validation scenarios:
- Empty required fields
- Invalid ICP principal format
- Appropriate error messages displayed

### 3. Network Selection

Tests that:
- All 4 networks are available (ICP, Bitcoin, Ethereum, SEPA)
- Currency dropdown updates based on selected network
- ICP shows: ICP, ckBTC, ckETH
- Bitcoin shows: BTC
- Ethereum shows: ETH, USDC, USDT
- SEPA shows: EUR

### 4. Account Removal

Tests:
- Remove button visibility
- Confirmation dialog appears
- Account is removed from list after confirmation

### 5. Empty State

Tests proper handling when no accounts exist:
- Empty state message displayed
- Appropriate user guidance shown

## Configuration

- **Base URL**: `http://localhost:8000` (configurable via `PLAYWRIGHT_BASE_URL` env variable)
- **Timeout**: 30 seconds per test
- **Retries**: 5 (for flaky test handling)
- **Browser**: Chromium (Chrome)
- **Parallel Execution**: Disabled (workers: 1)
- **Screenshots**: On failure
- **Video**: On failure

## Test Data

Tests use sample ICP addresses in the correct format:
- `test1-test2-test3-test4-test5-test6-test7-test8-test9-testa-eqe`
- `xyz11-abc22-def33-ghi44-jkl55-mno66-pqr77-stu88-vwx99-yza00-eqe`

## Debugging Failed Tests

1. **Check screenshots** (saved in `test-results/` directory)
2. **Review video recordings** (saved in `test-results/` directory)
3. **Use debug mode**:
   ```bash
   npm run test:debug
   ```
4. **Check browser console** in headed mode
5. **Verify backend is running**:
   ```bash
   dfx canister status realm_backend
   ```

## CI/CD Integration

These tests are designed to run in CI environments:
- Fail fast on first failure (`maxFailures: 1`)
- Retry flaky tests automatically (5 retries)
- Generate HTML reports
- Capture screenshots and videos on failure

## Known Limitations

1. Tests require a running local dfx environment
2. Tests assume user is authenticated (or test can run anonymously)
3. Some tests may be flaky due to network timing - retries are configured
4. First test run may be slower due to canister cold start

## Future Enhancements

- [ ] Add tests for Bitcoin address validation
- [ ] Add tests for Ethereum address validation
- [ ] Add tests for SEPA IBAN validation
- [ ] Add tests for account verification status
- [ ] Add tests for duplicate address prevention
- [ ] Add tests for pagination (if many accounts)
- [ ] Add tests for account editing functionality
- [ ] Add performance benchmarks
