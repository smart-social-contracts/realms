# Member Dashboard E2E Tests

End-to-end tests for the Member Dashboard extension using Playwright.

## Setup

Install dependencies:

```bash
cd extensions/member_dashboard/tests/e2e
npm install
npx playwright install chromium
```

## Running Tests

### Prerequisites
- Realm must be deployed and running (locally or on a network)
- Set `PLAYWRIGHT_BASE_URL` environment variable to your realm's URL

### Local Development

```bash
# Run all tests
npm test

# Run with browser visible
npm run test:headed

# Run in debug mode (step through tests)
npm run test:debug

# Run with Playwright UI (interactive mode)
npm run test:ui
```

### CI/CD

```bash
# Run against deployed realm
PLAYWRIGHT_BASE_URL=http://localhost:8000 npm test

# Run against staging
PLAYWRIGHT_BASE_URL=https://your-staging-url.icp0.io npm test
```

## Test Structure

### member_dashboard.spec.ts
Comprehensive E2E tests covering:

1. **Page Load & Navigation**
   - Dashboard page loads successfully
   - Main sections are visible
   - Navigation between sections works

2. **Dashboard Summary**
   - Summary statistics are displayed
   - Cards show correct counts
   - Data refreshes properly

3. **Public Services**
   - Services list displays
   - Service provider information shown
   - Service details are accessible

4. **Tax Information/Invoices**
   - Invoice list displays
   - Status indicators work (Paid, Pending, Overdue)
   - Due dates are shown
   - Financial totals are calculated

5. **Personal Data**
   - Personal information section loads
   - User data is displayed correctly

6. **Error Handling**
   - Empty states display gracefully
   - Error messages are user-friendly
   - Failed API calls show appropriate feedback

## Configuration

See `playwright.config.ts` for test configuration:
- Timeout: 30 seconds per test
- Retries: 5 (for flaky network conditions)
- Workers: 1 (sequential execution)
- Screenshots and videos on failure

## Debugging Failed Tests

1. **View screenshots**: Check `playwright-report/` folder after test run
2. **Watch videos**: Videos are saved for failed tests
3. **Use debug mode**: `npm run test:debug` to step through tests
4. **Check traces**: Traces are collected on first retry

## Best Practices

- Tests are designed to be resilient to UI changes
- Uses semantic selectors (roles, labels) over CSS selectors
- Handles loading states and async operations
- Provides meaningful timeouts for CI environments
- Gracefully handles optional features

## Adding New Tests

When adding features to the Member Dashboard:

1. Add new test cases to `specs/member_dashboard.spec.ts`
2. Follow existing patterns for waiting and assertions
3. Use descriptive test names
4. Handle both success and error cases
5. Consider empty states and edge cases

## Troubleshooting

**Tests timing out:**
- Increase timeout in `playwright.config.ts`
- Check that realm is actually running at `PLAYWRIGHT_BASE_URL`
- Verify network connectivity

**Elements not found:**
- Check if UI text changed
- Verify the extension is installed in the realm
- Use `test:debug` to inspect the actual page state

**Flaky tests:**
- Tests auto-retry 5 times
- Check for race conditions in async operations
- Add appropriate waits for dynamic content
