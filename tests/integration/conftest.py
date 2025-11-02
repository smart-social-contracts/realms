"""Integration test configuration.

Note: These tests are standalone Python scripts (no pytest required).
They assume dfx is already running with a deployed realm.

In CI, this is handled by the workflow starting a container with the realm deployed.

For local testing, ensure you have run:
  - dfx start --clean --background
  - realms create && realms deploy

Then run:
  - bash tests/integration/run_tests.sh
  or
  - python3 tests/integration/test_status_api.py
"""
