# Member Dashboard Extension Tests

Comprehensive test suite for the member_dashboard extension to catch issues early.

## Test Types

### 1. Backend/Integration Tests (Python)
Tests for backend functionality and data integrity.

### 2. End-to-End Tests (Playwright/TypeScript)
Tests for frontend UI and user interactions.

## Test Files

### test_imports.py
Simple import test that can run standalone without a deployed realm. Validates:
- Core entity imports (Invoice, Service, User)
- Extension module structure
- API function presence

**Run locally:**
```bash
cd extensions/member_dashboard/tests
python test_imports.py
```

### test_member_dashboard.py
Integration test that runs against a deployed realm. Tests:
- Invoice and Service entity queries
- Extension API endpoints (get_dashboard_summary, get_public_services, get_tax_information)
- Data validation and response structure

**Run against deployed realm:**
```bash
# From realm root
realms run --file extensions/member_dashboard/tests/test_member_dashboard.py --wait

# Or using the helper script
./extensions/member_dashboard/tests/run_tests.sh
```

## CI Integration

These tests should be added to the CI pipeline to catch issues like:
- Missing imports (e.g., TaxRecord → Invoice refactoring)
- API function signature changes
- Data structure mismatches
- Extension installation failures

## Expected Output

**Import Test:**
```
Testing member_dashboard imports...
✓ Successfully imported: Invoice, Service, User
✓ Invoice entity structure validated
✓ Successfully imported member_dashboard.entry module
✓ All expected API functions present
✅ All imports successful!
```

**Integration Test:**
```
Starting member dashboard tests...
Test 1: Query invoices...
✓ Found 4 invoices
  Sample invoice ID: invoice-001
  Amount: 2450.75
  Status: Pending
Test 2: Query services...
✓ Found X services
...
Member dashboard tests completed!
```

### e2e/ - Playwright End-to-End Tests
Browser-based UI tests for the Member Dashboard extension. Tests the complete user experience including:
- Page navigation and loading
- Dashboard summary displays
- Public services listing
- Tax information/invoices display
- Personal data sections
- User interactions and error handling

**Run E2E tests:**
```bash
cd extensions/member_dashboard/tests/e2e
npm install
npx playwright install chromium
PLAYWRIGHT_BASE_URL=http://localhost:8000 npm test
```

See `e2e/README.md` for detailed documentation.

## Adding New Tests

When adding new functionality to the extension:

### Backend Tests
1. Add API function presence check to `test_imports.py`
2. Add functional test to `test_member_dashboard.py`
3. Update this README with new test descriptions

### E2E Tests
1. Add new test cases to `e2e/specs/member_dashboard.spec.ts`
2. Follow existing patterns for UI interactions
3. Test both success and error scenarios
4. Update `e2e/README.md` if adding new test categories
