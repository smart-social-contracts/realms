#!/usr/bin/env python3
"""
Geister Agent Swarm Test - Run LLM-powered agents against staging realms.

Discovers realms dynamically from the registry and runs agents that join
and perform operations via the geister API.

Usage:
    python test_agent_swarm.py
    AGENTS_COUNT=100 python test_agent_swarm.py
"""
import json
import os
import sys
import re
import subprocess
import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Configuration - easily changeable
AGENTS_COUNT = int(os.getenv("AGENTS_COUNT", "3"))  # Total agents distributed across all realms
NETWORK = os.getenv("NETWORK", "staging")
GEISTER_API_URL = os.getenv("GEISTER_API_URL", "https://geister-api.realmsgos.dev")
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "5"))
FAILURE_THRESHOLD = float(os.getenv("FAILURE_THRESHOLD", "0.2"))  # 20% max failures allowed
LOGS_DIR = Path(os.getenv("LOGS_DIR", "agent_logs"))


def discover_realms() -> List[Dict[str, str]]:
    """Discover realms from the registry."""
    print(f"Discovering realms from registry (network: {NETWORK})...")
    
    try:
        result = subprocess.run(
            ["realms", "registry", "list", "--network", NETWORK],
            capture_output=True, text=True, timeout=60
        )
        
        if result.returncode != 0:
            print(f"Error listing registry: {result.stderr}")
            return []
        
        # Parse the Candid-style output
        # Looking for: id = "xxx"; name = "yyy";
        realms = []
        output = result.stdout
        
        # Find all records
        records = re.findall(r'record\s*\{([^}]+)\}', output, re.DOTALL)
        
        for record in records:
            realm = {}
            # Extract id
            id_match = re.search(r'id\s*=\s*"([^"]+)"', record)
            if id_match:
                realm['id'] = id_match.group(1)
            
            # Extract name
            name_match = re.search(r'name\s*=\s*"([^"]+)"', record)
            if name_match:
                realm['name'] = name_match.group(1)
            
            # Extract url
            url_match = re.search(r'url\s*=\s*"([^"]+)"', record)
            if url_match:
                realm['url'] = url_match.group(1)
            
            if realm.get('id') and realm.get('name'):
                realms.append(realm)
        
        return realms
        
    except subprocess.TimeoutExpired:
        print("Timeout discovering realms")
        return []
    except Exception as e:
        print(f"Error discovering realms: {e}")
        return []


def run_agent_task(agent_id: str, realm_id: str, realm_name: str, task: str) -> Tuple[str, str, bool, str, dict]:
    """Run a single agent task and return (agent_id, realm_name, success, result, full_log)."""
    full_log = {
        "agent_id": agent_id,
        "realm_id": realm_id,
        "realm_name": realm_name,
        "task": task,
        "timestamp": datetime.now().isoformat(),
        "stdout": "",
        "stderr": "",
        "returncode": None,
        "parsed_response": None,
        "success": False,
        "error": None
    }
    
    try:
        cmd = [
            "geister", "agent", "ask", agent_id, task,
            "--realm", realm_id,
            "--json",  # Use structured JSON output for reliable success detection
            "--api-url", GEISTER_API_URL,  # Use configured API URL
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        full_log["stdout"] = result.stdout
        full_log["stderr"] = result.stderr
        full_log["returncode"] = result.returncode
        
        # Parse JSON response for reliable success detection
        try:
            data = json.loads(result.stdout)
            full_log["parsed_response"] = data
            success = data.get("success", False)
            full_log["success"] = success
            response = data.get("response", "")[:500]
            error = data.get("error")
            if error:
                full_log["error"] = error
                return (agent_id, realm_name, False, f"Error: {error}", full_log)
            return (agent_id, realm_name, success, response, full_log)
        except json.JSONDecodeError as e:
            # Fallback if JSON parsing fails
            full_log["error"] = f"JSON decode error: {e}"
            output = result.stdout + result.stderr
            return (agent_id, realm_name, result.returncode == 0, output[:500], full_log)
        
    except subprocess.TimeoutExpired:
        full_log["error"] = "Timeout after 180s"
        return (agent_id, realm_name, False, "Timeout", full_log)
    except Exception as e:
        full_log["error"] = str(e)
        return (agent_id, realm_name, False, str(e), full_log)


def run_agent_swarm(realms: List[Dict[str, str]]) -> Dict:
    """Run agents against all realms."""
    results = {
        "total_success": 0,
        "total_failed": 0,
        "realms": []
    }
    
    tasks = []
    
    # Initialize realm results
    realm_results = {}
    for realm in realms:
        realm_result = {
            "name": realm['name'],
            "id": realm['id'],
            "success": 0,
            "failed": 0,
            "agents": []
        }
        results["realms"].append(realm_result)
        realm_results[realm['id']] = realm_result
    
    # Distribute agents across realms (round-robin)
    for agent_num in range(1, AGENTS_COUNT + 1):
        realm = realms[(agent_num - 1) % len(realms)]
        agent_id = f"swarm_agent_{agent_num:03d}"
        task = "Please join this realm as a member. After joining successfully, use db_schema to discover available entity types, then use db_get to check for any Notification entities. If there are notifications with instructions, follow those instructions. Report what actions you took."
        tasks.append((agent_id, realm['id'], realm['name'], task, realm_results[realm['id']]))
    
    print(f"\nRunning {AGENTS_COUNT} agents across {len(realms)} realms...")
    print(f"(AGENTS_COUNT={AGENTS_COUNT}, MAX_WORKERS={MAX_WORKERS})")
    print("=" * 60)
    
    # Create logs directory
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    all_logs = []
    
    # Run tasks in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for agent_id, realm_id, realm_name, task, realm_result in tasks:
            future = executor.submit(run_agent_task, agent_id, realm_id, realm_name, task)
            futures[future] = realm_result
        
        for future in concurrent.futures.as_completed(futures):
            realm_result = futures[future]
            agent_id, realm_name, success, output, full_log = future.result()
            all_logs.append(full_log)
            
            # Save individual agent log
            log_file = LOGS_DIR / f"{agent_id}_{realm_name.replace(' ', '_')}.json"
            with open(log_file, 'w') as f:
                json.dump(full_log, f, indent=2)
            
            if success:
                realm_result["success"] += 1
                results["total_success"] += 1
                print(f"  ✅ {agent_id} -> {realm_name}")
            else:
                realm_result["failed"] += 1
                results["total_failed"] += 1
                # Show first line of error
                error_line = output.split('\n')[0][:80] if output else "Unknown error"
                print(f"  ❌ {agent_id} -> {realm_name}: {error_line}")
            
            realm_result["agents"].append({
                "agent_id": agent_id,
                "success": success,
                "output": output[:200]
            })
    
    # Save combined logs
    combined_log_file = LOGS_DIR / "all_agents.json"
    with open(combined_log_file, 'w') as f:
        json.dump(all_logs, f, indent=2)
    print(f"\n📋 Agent logs saved to {LOGS_DIR}/")
    
    return results


def print_summary(results: Dict):
    """Print test summary."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for realm in results["realms"]:
        total = realm["success"] + realm["failed"]
        pct = 100 * realm["success"] / total if total > 0 else 0
        print(f"  {realm['name']}: {realm['success']}/{total} successful ({pct:.0f}%)")
    
    total = results["total_success"] + results["total_failed"]
    if total > 0:
        pct = 100 * results["total_success"] / total
        print(f"\n  TOTAL: {results['total_success']}/{total} successful ({pct:.1f}%)")
    else:
        print("\n  TOTAL: No agents ran")


def main():
    print("=" * 60)
    print("GEISTER AGENT SWARM TEST")
    print("=" * 60)
    print(f"API URL: {GEISTER_API_URL}")
    print(f"Network: {NETWORK}")
    print(f"Total agents: {AGENTS_COUNT}")
    
    # Discover realms
    realms = discover_realms()
    
    if not realms:
        print("\n❌ No realms found in registry")
        sys.exit(1)
    
    print(f"\nFound {len(realms)} realms:")
    for realm in realms:
        print(f"  - {realm['name']} ({realm['id']})")
    
    # Run agent swarm
    results = run_agent_swarm(realms)
    
    # Print summary
    print_summary(results)
    
    # Check failure threshold
    total = results["total_success"] + results["total_failed"]
    if total > 0:
        failure_rate = results["total_failed"] / total
        if failure_rate > FAILURE_THRESHOLD:
            print(f"\n❌ Failure rate ({failure_rate:.1%}) exceeds threshold ({FAILURE_THRESHOLD:.0%})")
            sys.exit(1)
    
    print("\n✅ Agent swarm test passed")
    sys.exit(0)


if __name__ == "__main__":
    main()
