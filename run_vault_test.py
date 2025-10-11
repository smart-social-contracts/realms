from core.task_manager import Call, Task, TaskStep, TaskManager
from ggg import Codex
from ggg.task_schedule import TaskSchedule
import time
from kybra import ic
import traceback

ic.print('Running Vault Test via TaskManager')

codex = Codex["test_vault_in_realm"]
if not codex:
    ic.print("ERROR: Codex not found!")
else:
    try:
        ic.print(f"Found codex = {codex.name}")
        call = Call()
        call.is_async = True
        call.codex = codex

        ic.print("1")
        step = TaskStep(call=call)

        ic.print("2")
        task = Task(name="Vault Status Test", steps=[step])

        ic.print("3")
        schedule = TaskSchedule(task=task)
        # task.schedules = [schedule]
        
        manager = TaskManager()
        manager.add_task(task)

        ic.print('About to run')

        manager.run()
        ic.print(f"Task Status: {task.status}")
        ic.print(f"Step Status: {step.status}")
        ic.print("Check canister logs for async execution results")
    except Exception as e:
        ic.print(traceback.format_exc())