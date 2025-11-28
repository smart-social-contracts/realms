# Quick Start Guide - Vault E2E Tests

## 🚀 Running Tests Locally

### Step 1: Deploy the Realm and Vault Test Canisters

```bash
cd /home/user/dev/smartsocialcontracts/integration/realms/extensions/vault
./run_tests_dev.sh
```

This will:
- Deploy all canisters
- Create 101 test transactions
- Sync transactions to the vault

### Step 2: Run the E2E Tests

```bash
cd tests/e2e
./run-e2e-tests.sh
```

That's it! The test runner will:
- Install dependencies automatically (first run only)
- Detect the canister URL
- Run all Playwright tests
- Generate a test report

## 📊 View Test Results

After tests complete:

```bash
# View HTML report
npx playwright show-report
```

## 🎭 Interactive Testing

### Run tests in UI mode (recommended for development)
```bash
npm run test:ui
```

### Run tests with browser visible
```bash
npm run test:headed
```

### Debug a specific test
```bash
npm run test:debug -- specs/vault.spec.ts
```

## 📝 What Gets Tested

- ✅ Vault Manager page loads correctly
- ✅ All tabs (Balance, Transactions, Transfer, Admin) are accessible
- ✅ Vault principal is displayed and copyable
- ✅ Last refresh timestamp shows and updates
- ✅ Transaction table displays with proper columns
- ✅ Pagination works (Previous/Next, page numbers)
- ✅ Principals are clickable and copyable
- ✅ Timestamps are human-readable and copyable
- ✅ Balance information displays correctly
- ✅ Transfer form validates inputs
- ✅ Admin panel shows system information
- ✅ Refresh button updates data

## 🔧 Customization

Edit `specs/vault.spec.ts` to add more tests or modify existing ones.

## 🐛 Troubleshooting

**Problem:** `Could not get realm_frontend canister ID`
**Solution:** Run `./run_tests_dev.sh` first to deploy canisters

**Problem:** Browser downloads fail
**Solution:** Run `npx playwright install chromium`

**Problem:** Tests timeout
**Solution:** Increase timeout in test files or config

## 📚 More Information

See `README.md` for detailed documentation.
