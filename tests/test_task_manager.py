"""
DEPRECATED: This test file is outdated and tests components that no longer exist.

The TaskManager implementation has changed from a queue/cron-based system to a
timer/schedule-based system using Internet Computer timers and TaskSchedule entities.

This file tests:
- QueuedTask (doesn't exist anymore)
- Cron scheduling (replaced by TaskSchedule with run_at/repeat_every)
- Queue operations (replaced by entity-based task management)

For current integration tests, see:
    tests/integration/test_task_manager_api.py

The new tests verify:
- execute_code() API endpoint (sync and async code execution)
- get_task_status() API endpoint (task status polling)
- TaskManager with Call, TaskStep, Task, and TaskSchedule entities
- Codex execution integration
- Timer-based task scheduling

To run the current integration tests:
    cd tests/integration
    python3 test_task_manager_api.py

Or run all integration tests:
    bash tests/integration/run_tests.sh
"""

import sys

def main():
    print("\n" + "=" * 70)
    print("⚠️  DEPRECATED TEST FILE")
    print("=" * 70)
    print(__doc__)
    print("=" * 70 + "\n")
    sys.exit(1)

if __name__ == "__main__":
    main()
