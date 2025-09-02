#!/usr/bin/env python3
"""
Setup Script for Generated Realm Codexes

Creates Tasks with proper scheduling to run the generated governance codexes:
- Tax Collection Codex (monthly on 15th)
- Social Benefits Codex (monthly on 1st) 
- Governance Automation Codex (weekly on Mondays)

Usage:
    python setup.py --realm-dir generated_realm
"""

import argparse
import sys
import os
from pathlib import Path

# Add the realm backend to the path so we can import the required classes
sys.path.append('/home/user/dev/smartsocialcontracts/realms2/src/realm_backend')

from core.task_manager import Task, TaskStep, Call, TaskManager
from ggg.codex import Codex
from ggg.task_schedule import TaskSchedule
from kybra_simple_logging import get_logger

logger = get_logger("setup")

def create_tax_collection_task(codex_file_path: str) -> Task:
    """Create a task for tax collection automation"""
    logger.info("Creating tax collection task")
    
    # Read the codex file
    with open(codex_file_path, 'r') as f:
        codex_code = f.read()
    
    # Create the codex
    codex = Codex()
    codex.name = "Tax Collection Automation"
    codex.description = "Automated tax calculation and collection system"
    codex.code = codex_code
    
    # Create sync call for the codex
    sync_call = Call()
    sync_call.is_async = False
    sync_call.codex = codex
    
    # Create task step
    step = TaskStep(call=sync_call)
    
    # Create the task
    task = Task(
        name="Monthly Tax Collection",
        steps=[step]
    )
    task.metadata = '{"description": "Monthly automated tax collection", "category": "finance"}'
    
    # Create schedule - monthly on 15th at midnight
    schedule = TaskSchedule(cron_expression="0 0 15 * *")  # 15th of every month
    schedule.task = task
    task.schedules = [schedule]
    
    logger.info("Tax collection task created successfully")
    return task

def create_social_benefits_task(codex_file_path: str) -> Task:
    """Create a task for social benefits distribution"""
    logger.info("Creating social benefits task")
    
    # Read the codex file
    with open(codex_file_path, 'r') as f:
        codex_code = f.read()
    
    # Create the codex
    codex = Codex()
    codex.name = "Social Benefits Distribution"
    codex.description = "Automated social benefits eligibility and distribution system"
    codex.code = codex_code
    
    # Create sync call for the codex
    sync_call = Call()
    sync_call.is_async = False
    sync_call.codex = codex
    
    # Create task step
    step = TaskStep(call=sync_call)
    
    # Create the task
    task = Task(
        name="Monthly Benefits Distribution",
        steps=[step]
    )
    task.metadata = '{"description": "Monthly social benefits distribution", "category": "social_services"}'
    
    # Create schedule - monthly on 1st at midnight
    schedule = TaskSchedule(cron_expression="0 0 1 * *")  # 1st of every month
    schedule.task = task
    task.schedules = [schedule]
    
    logger.info("Social benefits task created successfully")
    return task

def create_governance_automation_task(codex_file_path: str) -> Task:
    """Create a task for governance automation"""
    logger.info("Creating governance automation task")
    
    # Read the codex file
    with open(codex_file_path, 'r') as f:
        codex_code = f.read()
    
    # Create the codex
    codex = Codex()
    codex.name = "Governance Automation"
    codex.description = "Automated proposal processing and vote tallying system"
    codex.code = codex_code
    
    # Create sync call for the codex
    sync_call = Call()
    sync_call.is_async = False
    sync_call.codex = codex
    
    # Create task step
    step = TaskStep(call=sync_call)
    
    # Create the task
    task = Task(
        name="Weekly Governance Processing",
        steps=[step]
    )
    task.metadata = '{"description": "Weekly governance proposal processing", "category": "governance"}'
    
    # Create schedule - weekly on Mondays at midnight
    schedule = TaskSchedule(cron_expression="0 0 * * 1")  # Every Monday
    schedule.task = task
    task.schedules = [schedule]
    
    logger.info("Governance automation task created successfully")
    return task

def create_immediate_test_task(codex_file_path: str, task_name: str) -> Task:
    """Create a task that runs immediately for testing purposes"""
    logger.info(f"Creating immediate test task for {task_name}")
    
    # Read the codex file
    with open(codex_file_path, 'r') as f:
        codex_code = f.read()
    
    # Create the codex
    codex = Codex()
    codex.name = f"{task_name} Test"
    codex.description = f"Immediate test execution of {task_name}"
    codex.code = codex_code
    
    # Create sync call for the codex
    sync_call = Call()
    sync_call.is_async = False
    sync_call.codex = codex
    
    # Create task step
    step = TaskStep(call=sync_call)
    
    # Create the task
    task = Task(
        name=f"Test {task_name}",
        steps=[step]
    )
    task.metadata = f'{{"description": "Immediate test of {task_name}", "category": "testing"}}'
    
    # Create schedule - run immediately and don't repeat
    schedule = TaskSchedule(run_at=0, repeat_every=0)  # Run once immediately
    schedule.task = task
    task.schedules = [schedule]
    
    logger.info(f"Test task for {task_name} created successfully")
    return task

def setup_realm_tasks(realm_dir: str, test_mode: bool = False) -> None:
    """Setup all tasks for the generated realm"""
    realm_path = Path(realm_dir)
    
    if not realm_path.exists():
        raise FileNotFoundError(f"Realm directory not found: {realm_dir}")
    
    # Expected codex files
    codex_files = {
        "tax_collection": realm_path / "tax_collection_codex.py",
        "social_benefits": realm_path / "social_benefits_codex.py", 
        "governance_automation": realm_path / "governance_automation_codex.py"
    }
    
    # Verify all codex files exist
    missing_files = []
    for name, file_path in codex_files.items():
        if not file_path.exists():
            missing_files.append(str(file_path))
    
    if missing_files:
        raise FileNotFoundError(f"Missing codex files: {missing_files}")
    
    # Create task manager
    task_manager = TaskManager()
    
    # Create tasks
    tasks_created = []
    
    if test_mode:
        # Create immediate test tasks
        logger.info("Creating test tasks (immediate execution)")
        
        tax_task = create_immediate_test_task(
            str(codex_files["tax_collection"]), 
            "Tax Collection"
        )
        task_manager.add_task(tax_task)
        tasks_created.append(tax_task.name)
        
        benefits_task = create_immediate_test_task(
            str(codex_files["social_benefits"]), 
            "Social Benefits"
        )
        task_manager.add_task(benefits_task)
        tasks_created.append(benefits_task.name)
        
        governance_task = create_immediate_test_task(
            str(codex_files["governance_automation"]), 
            "Governance Automation"
        )
        task_manager.add_task(governance_task)
        tasks_created.append(governance_task.name)
        
    else:
        # Create scheduled tasks
        logger.info("Creating scheduled tasks")
        
        tax_task = create_tax_collection_task(str(codex_files["tax_collection"]))
        task_manager.add_task(tax_task)
        tasks_created.append(tax_task.name)
        
        benefits_task = create_social_benefits_task(str(codex_files["social_benefits"]))
        task_manager.add_task(benefits_task)
        tasks_created.append(benefits_task.name)
        
        governance_task = create_governance_automation_task(str(codex_files["governance_automation"]))
        task_manager.add_task(governance_task)
        tasks_created.append(governance_task.name)
    
    # Run the task manager
    logger.info("Starting task manager...")
    task_manager.run()
    
    logger.info(f"Setup completed successfully. Created {len(tasks_created)} tasks:")
    for task_name in tasks_created:
        logger.info(f"  - {task_name}")
    
    if test_mode:
        logger.info("Test mode: Tasks will execute immediately")
    else:
        logger.info("Production mode: Tasks scheduled according to cron expressions")
        logger.info("  - Tax Collection: Monthly on 15th")
        logger.info("  - Social Benefits: Monthly on 1st") 
        logger.info("  - Governance: Weekly on Mondays")

def main():
    parser = argparse.ArgumentParser(description="Setup tasks for generated realm codexes")
    parser.add_argument("--realm-dir", type=str, required=True, help="Directory containing generated realm codexes")
    parser.add_argument("--test", action="store_true", help="Run in test mode (immediate execution)")
    
    args = parser.parse_args()
    
    try:
        setup_realm_tasks(args.realm_dir, test_mode=args.test)
        print("✅ Realm tasks setup completed successfully!")
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logger.error(f"Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
