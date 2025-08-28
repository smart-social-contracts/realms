"""
Test TaskManager integration with the Realms system
"""

import sys
import os

# Add the src directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'realm_backend'))

def test_task_manager_basic():
    """Test basic TaskManager functionality"""
    print("Testing TaskManager basic functionality...")
    
    try:
        from core.task_manager import TaskManager, TaskStatus, QueuedTask
        
        # Test singleton pattern
        tm1 = TaskManager()
        tm2 = TaskManager()
        assert tm1 is tm2, "TaskManager should be a singleton"
        print("✓ Singleton pattern works")
        
        # Test QueuedTask creation
        task = QueuedTask("test_id", "Test Task")
        assert task.status == TaskStatus.PENDING
        assert task.task_id == "test_id"
        assert task.task_name == "Test Task"
        print("✓ QueuedTask creation works")
        
        # Test queue status
        status = tm1.get_queue_status()
        assert "queue_size" in status
        assert "processing" in status
        assert "pending_tasks" in status
        print("✓ Queue status retrieval works")
        
        print("✓ All basic TaskManager tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ TaskManager basic test failed: {e}")
        return False


def test_task_manager_with_mock_task():
    """Test TaskManager with a mock task"""
    print("\nTesting TaskManager with mock task...")
    
    try:
        from core.task_manager import task_manager
        from ggg.task import Task
        from ggg.codex import Codex
        
        # Note: This test assumes we can create mock entities
        # In a real environment, you'd need actual Task and Codex entities
        
        # Test adding a non-existent task (should fail gracefully)
        success = task_manager.add_task_to_queue("non_existent_task")
        assert not success, "Adding non-existent task should fail"
        print("✓ Non-existent task handling works")
        
        # Test queue operations
        initial_size = len(task_manager.queue)
        task_manager.clear_queue()
        assert len(task_manager.queue) == 0, "Queue should be empty after clear"
        print("✓ Queue clearing works")
        
        print("✓ Mock task tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Mock task test failed: {e}")
        return False


def test_cron_functionality():
    """Test cron scheduling functionality"""
    print("\nTesting cron functionality...")
    
    try:
        from core.task_manager import TaskManager
        from datetime import datetime, timezone
        
        tm = TaskManager()
        
        # Test basic cron expressions
        current_time = datetime.now(timezone.utc)
        
        # Test wildcard (should always match)
        assert tm._should_run_cron("* * * * *", current_time), "Wildcard should always match"
        print("✓ Wildcard cron expression works")
        
        # Test specific minute match
        minute_expr = f"{current_time.minute} * * * *"
        assert tm._should_run_cron(minute_expr, current_time), "Current minute should match"
        print("✓ Specific minute matching works")
        
        # Test non-matching minute
        other_minute = (current_time.minute + 1) % 60
        non_match_expr = f"{other_minute} * * * *"
        assert not tm._should_run_cron(non_match_expr, current_time), "Different minute should not match"
        print("✓ Non-matching minute works")
        
        # Test step values
        assert tm._matches_cron_field("*/5", 0, 0, 59), "0 should match */5"
        assert tm._matches_cron_field("*/5", 5, 0, 59), "5 should match */5"
        assert not tm._matches_cron_field("*/5", 3, 0, 59), "3 should not match */5"
        print("✓ Step values work")
        
        # Test ranges
        assert tm._matches_cron_field("10-15", 12, 0, 59), "12 should match 10-15"
        assert not tm._matches_cron_field("10-15", 8, 0, 59), "8 should not match 10-15"
        print("✓ Range values work")
        
        # Test comma-separated values
        assert tm._matches_cron_field("1,3,5", 3, 0, 59), "3 should match 1,3,5"
        assert not tm._matches_cron_field("1,3,5", 4, 0, 59), "4 should not match 1,3,5"
        print("✓ Comma-separated values work")
        
        print("✓ Cron functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Cron functionality test failed: {e}")
        return False


def test_execution_integration():
    """Test integration with execution module"""
    print("\nTesting execution integration...")
    
    try:
        from core.execution import run_code
        
        # Test simple code execution
        result = run_code("result = 2 + 2")
        assert result["success"] == True
        assert result["result"] == 4
        print("✓ Simple code execution works")
        
        # Test code with error
        result = run_code("invalid_syntax ===")
        assert result["success"] == False
        assert "error" in result
        print("✓ Error handling in code execution works")
        
        print("✓ Execution integration tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Execution integration test failed: {e}")
        return False


def run_all_tests():
    """Run all TaskManager tests"""
    print("=" * 50)
    print("TASKMANAGER INTEGRATION TESTS")
    print("=" * 50)
    
    tests = [
        test_task_manager_basic,
        test_task_manager_with_mock_task,
        test_cron_functionality,
        test_execution_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All TaskManager integration tests passed!")
    else:
        print(f"⚠️  {total - passed} tests failed")
    
    print("=" * 50)
    return passed == total


if __name__ == "__main__":
    run_all_tests()
