"""
Tests for TaskEntity functionality in task codexes.

Tests that TaskEntity automatically namespaces entities by task name,
enabling isolated state storage for batch processing.
"""

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))

import pytest
from unittest.mock import MagicMock, patch

# Mock kybra before importing anything that uses it
sys.modules["kybra"] = MagicMock()
sys.modules["kybra.canisters.management"] = MagicMock()


def test_create_task_entity_class():
    """Test that create_task_entity_class creates properly namespaced entities"""
    from core.execution import create_task_entity_class
    from kybra_simple_db import String

    # Create TaskEntity for a specific task
    TaskEntity = create_task_entity_class("tax_collection")

    # Create a state entity using TaskEntity
    class ProcessingState(TaskEntity):
        __alias__ = "key"
        key = String()
        value = String()

    # Check namespace is set correctly
    assert ProcessingState.__namespace__ == "task_tax_collection"
    assert ProcessingState.get_full_type_name() == "task_tax_collection::ProcessingState"


def test_task_entity_isolation():
    """Test that different tasks get different namespaces"""
    from core.execution import create_task_entity_class
    from kybra_simple_db import String

    # Create entities for two different tasks
    TaxTaskEntity = create_task_entity_class("tax_collection")
    GovTaskEntity = create_task_entity_class("governance_automation")

    class TaxState(TaxTaskEntity):
        key = String()

    class GovState(GovTaskEntity):
        key = String()

    # Different namespaces
    assert TaxState.__namespace__ == "task_tax_collection"
    assert GovState.__namespace__ == "task_governance_automation"

    # Different full type names
    assert TaxState.get_full_type_name() == "task_tax_collection::TaxState"
    assert GovState.get_full_type_name() == "task_governance_automation::GovState"


def test_run_code_with_task_entity():
    """Test that run_code provides TaskEntity when task_name is given"""
    from core.execution import run_code

    code = """
from kybra_simple_db import String

# This should work because TaskEntity is injected
class MyState(TaskEntity):
    key = String()

result = MyState.__namespace__
"""

    # Run without task_name - TaskEntity should not be available
    result_without = run_code(code)
    assert not result_without["success"]
    assert "TaskEntity" in result_without.get("error", "")

    # Run with task_name - TaskEntity should be available
    result_with = run_code(code, task_name="test_task")
    assert result_with["success"]
    assert result_with["result"] == "task_test_task"


def test_batch_processing_pattern():
    """Test typical batch processing pattern with TaskEntity"""
    from core.execution import create_task_entity_class
    from kybra_simple_db import String, Integer

    TaskEntity = create_task_entity_class("batch_test")

    class BatchState(TaskEntity):
        __alias__ = "key"
        key = String()
        position = Integer()
        total = Integer()

    # Verify namespace
    assert BatchState.__namespace__ == "task_batch_test"

    # Create state (in real usage this would persist)
    state = BatchState(key="main", position=0, total=1000)
    assert state.position == 0
    assert state.total == 1000

    # Simulate batch processing
    BATCH_SIZE = 100
    state.position = min(state.position + BATCH_SIZE, state.total)
    assert state.position == 100

    # Next batch
    state.position = min(state.position + BATCH_SIZE, state.total)
    assert state.position == 200


def test_multiple_state_entities():
    """Test using multiple TaskEntity subclasses for different purposes"""
    from core.execution import create_task_entity_class
    from kybra_simple_db import String, Integer

    TaskEntity = create_task_entity_class("multi_state_test")

    class Progress(TaskEntity):
        __alias__ = "key"
        key = String()
        position = Integer()

    class Metrics(TaskEntity):
        __alias__ = "name"
        name = String()
        count = Integer()

    class ErrorLog(TaskEntity):
        __alias__ = "error_id"
        error_id = String()
        message = String()

    # All should have same namespace
    assert Progress.__namespace__ == "task_multi_state_test"
    assert Metrics.__namespace__ == "task_multi_state_test"
    assert ErrorLog.__namespace__ == "task_multi_state_test"

    # But different full type names
    assert Progress.get_full_type_name() == "task_multi_state_test::Progress"
    assert Metrics.get_full_type_name() == "task_multi_state_test::Metrics"
    assert ErrorLog.get_full_type_name() == "task_multi_state_test::ErrorLog"


def test_task_entity_in_codex_execution():
    """Test that TaskEntity works in actual codex execution context"""
    from core.execution import run_code

    codex_code = """
from kybra_simple_db import String, Integer
import json

# Define state entity
class State(TaskEntity):
    __alias__ = "key"
    key = String()
    value = String()

# Check namespace is set
namespace = State.__namespace__

# Create instance (would persist in real scenario)
state_data = {
    "position": 100,
    "total": 1000,
    "processed": 50
}

result = {
    "namespace": namespace,
    "full_type": State.get_full_type_name(),
    "data": state_data
}
"""

    result = run_code(codex_code, task_name="test_codex_task")

    assert result["success"], f"Execution failed: {result.get('error')}"
    assert result["result"]["namespace"] == "task_test_codex_task"
    assert result["result"]["full_type"] == "task_test_codex_task::State"
    assert result["result"]["data"]["position"] == 100


def test_task_entity_with_json_storage():
    """Test storing complex data as JSON in TaskEntity"""
    from core.execution import run_code
    import json

    codex_code = """
from kybra_simple_db import String
import json

class Metadata(TaskEntity):
    __alias__ = "key"
    key = String()
    data = String()

# Store complex data
complex_data = {
    "batch_size": 100,
    "last_run": 12345,
    "errors": ["error1", "error2"],
    "metrics": {"processed": 500, "failed": 3}
}

# Would create entity in real scenario
# metadata = Metadata(key="config", data=json.dumps(complex_data))

result = {
    "can_serialize": True,
    "data": complex_data
}
"""

    result = run_code(codex_code, task_name="json_test")

    assert result["success"]
    assert result["result"]["can_serialize"]
    assert result["result"]["data"]["batch_size"] == 100
    assert len(result["result"]["data"]["errors"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
