#!/usr/bin/env python3
"""
Geister Agent Swarm Test - Run LLM-powered agents against staging realms.

Discovers realms dynamically from the registry and runs a diverse swarm of
agents (assistants, founders, and citizens) that join and perform governance
operations via the Geister API.

Any issues self-reported by agents (prefixed ISSUE:) are automatically filed
as GitHub Issues using `gh issue create`.

Usage:
    python test_agent_swarm.py
    AGENTS_COUNT=22 python test_agent_swarm.py
    GITHUB_REPOSITORY=org/repo GH_TOKEN=xxx python test_agent_swarm.py
"""
import json
import os
import sys
import re
import subprocess
import time
import concurrent.futures
import requests as http_requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional, NamedTuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
AGENTS_COUNT = int(os.getenv("AGENTS_COUNT", "22"))   # agents per realm
NETWORK = os.getenv("NETWORK", "staging")
GEISTER_API_URL = os.getenv("GEISTER_API_URL", "https://geister-api.realmsgos.dev")
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "8"))
AGENT_TIMEOUT_SECONDS = int(os.getenv("AGENT_TIMEOUT_SECONDS", "300"))  # 5 min per agent
RUN_DURATION_MINUTES = int(os.getenv("RUN_DURATION_MINUTES", "0"))       # 0 = no overall limit
FAILURE_THRESHOLD = float(os.getenv("FAILURE_THRESHOLD", "0.3"))        # 30% max failures
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))                        # retry failed agents up to N times
RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", "10"))       # pause between retries
LOGS_DIR = Path(os.getenv("LOGS_DIR", "agent_logs"))
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY", "")   # e.g. "smart-social-contracts/realms"
GH_TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN", "")
ISSUE_LABEL = os.getenv("ISSUE_LABEL", "agent-swarm")
RUN_ID = os.getenv("RUN_ID") or os.getenv("GITHUB_RUN_ID") or datetime.now().strftime("%Y%m%d_%H%M%S")


# ---------------------------------------------------------------------------
# Persona roster definition
# AGENTS_COUNT agents are spread across realms using the ratio below.
# The list repeats as needed via modulo indexing.
# ---------------------------------------------------------------------------
class PersonaSlot(NamedTuple):
    persona: str           # name passed to geister --persona
    role_label: str        # human-readable label for logs
    emoji: str
    task: str              # LLM instruction for this agent


PERSONA_ROSTER: List[PersonaSlot] = [
    PersonaSlot(
        persona="ashoka",
        role_label="assistant",
        emoji="🏛️",
        task=(
            "Analyse this realm thoroughly. Use available tools to check realm status, "
            "active extensions, recent proposals, member count, and governance health. "
            "Summarise what you find. "
            "If anything looks broken, misconfigured, or suspicious, report it by writing "
            "'ISSUE: <one-line description>' on its own line for each problem found. "
            "Report what actions you took and what you observed."
        ),
    ),
    PersonaSlot(
        persona="founder",
        role_label="founder",
        emoji="🏗️",
        task=(
            "You are a visionary Founder. Create a new realm by doing ONLY these two calls "
            "(keep it fast, do NOT call anything else):\n"
            "1. Call get_my_principal.\n"
            "2. Call registry_deploy_realm with your principal and these fields:\n"
            "   realm_name – a creative unique name (add a random 3-char suffix like 'Aurora_7kx')\n"
            "   description – one sentence explaining the realm's vision\n"
            "   welcome_message – a short greeting for new citizens\n"
            "   logo_url – https://raw.githubusercontent.com/smart-social-contracts/realms/main/examples/demo/realm_new/emblem.png\n"
            "   welcome_image_url – https://raw.githubusercontent.com/smart-social-contracts/realms/main/examples/demo/realm_new/background.png\n"
            "If deploy fails with 'insufficient credits', call registry_redeem_voucher "
            "with your principal and code 'BETA50', then retry the deploy.\n"
            "Report any failure as 'ISSUE: <description>'. Summarise what you created."
        ),
    ),
    # 16 compliant citizens (slots 2..17)
    *[
        PersonaSlot(
            persona="compliant",
            role_label=f"citizen-compliant-{i}",
            emoji="✅",
            task=(
                "Join this realm as a member if you haven't already. "
                "Once joined, use db_schema to discover available entities. "
                "Check if there are any active proposals and cast a vote if possible. "
                "If anything fails or behaves unexpectedly, write 'ISSUE: <description>'. "
                "Report what actions you took."
            ),
        )
        for i in range(1, 17)
    ],
    # 2 watchful citizens (slots 18..19)
    *[
        PersonaSlot(
            persona="watchful",
            role_label=f"citizen-watchful-{i}",
            emoji="👁️",
            task=(
                "Join this realm and carefully observe its governance. "
                "Check the codex rules, active mandates, and any recent transfers. "
                "Look for anything unusual: policy loopholes, stale proposals, "
                "excessive permissions, or discrepancies. "
                "Write 'ISSUE: <description>' for every concern you notice. "
                "Report your full observations."
            ),
        )
        for i in range(1, 3)
    ],
    # 2 exploiter citizens (slots 20..21)
    *[
        PersonaSlot(
            persona="exploiter",
            role_label=f"citizen-exploiter-{i}",
            emoji="😈",
            task=(
                "Join this realm and try to find edge cases or weaknesses. "
                "Attempt actions that might fail gracefully or expose bugs: "
                "double-joining, voting on a closed proposal, calling an extension with "
                "bad arguments, or querying non-existent entities. "
                "Write 'ISSUE: <description>' for any unexpected error, crash message, "
                "or missing validation you encounter. "
                "Report everything you tried and what happened."
            ),
        )
        for i in range(1, 3)
    ],
]


# ---------------------------------------------------------------------------
# Agent registration (persistent profiles on the Geister API)
# ---------------------------------------------------------------------------

def _api_post(path: str, payload: Dict) -> Optional[Dict]:
    """POST JSON to the Geister API. Returns parsed response or None."""
    url = f"{GEISTER_API_URL}{path}"
    try:
        resp = http_requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except http_requests.exceptions.HTTPError as e:
        body = e.response.text[:200] if e.response is not None else ""
        code = e.response.status_code if e.response is not None else "?"
        print(f"  ⚠️  API POST {path} → HTTP {code}: {body}")
    except Exception as e:
        print(f"  ⚠️  API POST {path} failed: {e}")
    return None


def _api_put(path: str, payload: Dict) -> Optional[Dict]:
    """PUT JSON to the Geister API. Returns parsed response or None."""
    url = f"{GEISTER_API_URL}{path}"
    try:
        resp = http_requests.put(url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except http_requests.exceptions.HTTPError as e:
        body = e.response.text[:200] if e.response is not None else ""
        code = e.response.status_code if e.response is not None else "?"
        print(f"  ⚠️  API PUT {path} → HTTP {code}: {body}")
    except Exception as e:
        print(f"  ⚠️  API PUT {path} failed: {e}")
    return None


def register_agent(
    agent_id: str,
    display_name: str,
    persona: str,
    realm_name: str,
    realm_id: str,
    role_label: str,
) -> bool:
    """Register a persistent agent profile on the Geister API.

    The profile (and its telos) will survive the CI run so it is visible
    on the dashboard afterwards.
    """
    metadata = {
        "source": "agent-swarm-ci",
        "run_id": RUN_ID,
        "role_label": role_label,
        "realm_name": realm_name,
        "realm_id": realm_id,
        "network": NETWORK,
        "registered_at": datetime.now().isoformat(),
    }
    if GITHUB_REPOSITORY:
        metadata["github_repository"] = GITHUB_REPOSITORY

    result = _api_post("/api/agents", {
        "agent_id": agent_id,
        "display_name": display_name,
        "persona": persona,
        "metadata": metadata,
    })
    return result is not None and result.get("success", False)


def update_agent_after_run(agent_id: str, success: bool, issues: List[str], error: Optional[str] = None) -> None:
    """Update the agent's metadata with run results so they are visible on the dashboard."""
    metadata_patch: Dict = {
        "last_run_id": RUN_ID,
        "last_run_success": success,
        "last_run_at": datetime.now().isoformat(),
    }
    if issues:
        metadata_patch["last_run_issues"] = issues[:10]  # cap to avoid huge payloads
    if error:
        metadata_patch["last_run_error"] = str(error)[:500]
    _api_put(f"/api/agents/{agent_id}", {"metadata": metadata_patch})


def register_all_agents(tasks: List[Tuple]) -> int:
    """Register all agents with the Geister API. Returns count of successes."""
    print(f"\nRegistering {len(tasks)} agent(s) on {GEISTER_API_URL} (run_id={RUN_ID})...")
    registered = 0
    for agent_id, slot, realm_id, realm_name in tasks:
        ok = register_agent(
            agent_id=agent_id,
            display_name=agent_id,  # the API will generate a human name if it's a swarm_agent_NNN id
            persona=slot.persona,
            realm_name=realm_name,
            realm_id=realm_id,
            role_label=slot.role_label,
        )
        if ok:
            registered += 1
            print(f"  ✅ {agent_id} [{slot.role_label}] → {realm_name}")
        else:
            print(f"  ⚠️  {agent_id} [{slot.role_label}] → registration failed (will still attempt run)")
    print(f"Registered {registered}/{len(tasks)} agents\n")
    return registered


# ---------------------------------------------------------------------------
# Realm discovery
# ---------------------------------------------------------------------------

def discover_realms() -> List[Dict[str, str]]:
    """Discover realms from the registry via the realms CLI."""
    print(f"Discovering realms from registry (network: {NETWORK})...")
    try:
        result = subprocess.run(
            ["realms", "registry", "realm", "list", "--network", NETWORK],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            print(f"Error listing registry: {result.stderr}")
            return []

        realms = []
        records = re.findall(r"record\s*\{([^}]+)\}", result.stdout, re.DOTALL)
        for record in records:
            realm: Dict[str, str] = {}
            id_m = re.search(r'id\s*=\s*"([^"]+)"', record)
            name_m = re.search(r'name\s*=\s*"([^"]+)"', record)
            url_m = re.search(r'url\s*=\s*"([^"]+)"', record)
            if id_m:
                realm["id"] = id_m.group(1)
            if name_m:
                realm["name"] = name_m.group(1)
            if url_m:
                realm["url"] = url_m.group(1)
            if realm.get("id") and realm.get("name"):
                realms.append(realm)
        return realms

    except subprocess.TimeoutExpired:
        print("Timeout discovering realms")
        return []
    except Exception as e:
        print(f"Error discovering realms: {e}")
        return []


# ---------------------------------------------------------------------------
# Issue extraction
# ---------------------------------------------------------------------------

def extract_issues(text: str) -> List[str]:
    """Extract ISSUE: lines from agent response text."""
    issues = []
    for line in text.splitlines():
        m = re.match(r"\s*ISSUE:\s*(.+)", line, re.IGNORECASE)
        if m:
            issue_text = m.group(1).strip()
            if issue_text:
                issues.append(issue_text)
    return issues


# ---------------------------------------------------------------------------
# GitHub issue creation
# ---------------------------------------------------------------------------

def file_github_issue(title: str, body: str) -> bool:
    """File a GitHub issue using `gh issue create`. Returns True on success."""
    if not GITHUB_REPOSITORY or not GH_TOKEN:
        print(f"  ⚠️  Skipping GitHub issue creation (no GITHUB_REPOSITORY or GH_TOKEN)")
        return False
    try:
        env = {**os.environ, "GH_TOKEN": GH_TOKEN}
        result = subprocess.run(
            [
                "gh", "issue", "create",
                "--repo", GITHUB_REPOSITORY,
                "--title", f"[agent-swarm] {title[:120]}",
                "--body", body[:65000],  # GH has a body size limit
                "--label", ISSUE_LABEL,
            ],
            capture_output=True, text=True, timeout=30, env=env,
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            print(f"  📝 Filed GitHub issue: {url}")
            return True
        else:
            print(f"  ⚠️  gh issue create failed: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"  ⚠️  Error filing GitHub issue: {e}")
        return False


# ---------------------------------------------------------------------------
# Single agent task runner
# ---------------------------------------------------------------------------

def run_agent_task(
    agent_id: str,
    slot: PersonaSlot,
    realm_id: str,
    realm_name: str,
) -> Dict:
    """Run one agent against one realm. Returns a structured log dict."""
    log: Dict = {
        "agent_id": agent_id,
        "realm_id": realm_id,
        "realm_name": realm_name,
        "persona": slot.persona,
        "role_label": slot.role_label,
        "timestamp": datetime.now().isoformat(),
        "stdout": "",
        "stderr": "",
        "returncode": None,
        "parsed_response": None,
        "success": False,
        "error": None,
        "issues": [],
    }

    try:
        cmd = [
            "geister", "agent", "ask", agent_id, slot.task,
            "--persona", slot.persona,
            "--realm", realm_id,
            "--json",
            "--api-url", GEISTER_API_URL,
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=AGENT_TIMEOUT_SECONDS,
        )
        log["stdout"] = result.stdout
        log["stderr"] = result.stderr
        log["returncode"] = result.returncode

        # Parse JSON response
        try:
            data = json.loads(result.stdout)
            log["parsed_response"] = data
            response_text = data.get("response", "")
            error = data.get("error")
            if error:
                log["error"] = error
                log["success"] = False
            else:
                log["success"] = data.get("success", False)
                log["issues"] = extract_issues(response_text)
        except json.JSONDecodeError as e:
            log["error"] = f"JSON decode error: {e}"
            log["success"] = result.returncode == 0
            log["issues"] = extract_issues(result.stdout + result.stderr)

    except subprocess.TimeoutExpired:
        log["error"] = f"Timeout after {AGENT_TIMEOUT_SECONDS}s"
    except Exception as e:
        log["error"] = str(e)

    return log


# ---------------------------------------------------------------------------
# Swarm runner
# ---------------------------------------------------------------------------

def build_task_list(realms: List[Dict]) -> List[Tuple]:
    """
    For each realm, spawn AGENTS_COUNT agents, assigning persona slots
    in order from PERSONA_ROSTER via modulo indexing.
    """
    tasks = []
    agent_counter = 0
    for realm in realms:
        for i in range(AGENTS_COUNT):
            slot = PERSONA_ROSTER[i % len(PERSONA_ROSTER)]
            agent_counter += 1
            agent_id = f"swarm_agent_{agent_counter:03d}"
            tasks.append((agent_id, slot, realm["id"], realm["name"]))
    return tasks


def run_agent_swarm(realms: List[Dict]) -> Dict:
    """Run the full agent swarm and return aggregated results."""
    results: Dict = {
        "total_success": 0,
        "total_failed": 0,
        "total_issues": 0,
        "realms": {},
        "all_issues": [],
    }

    for realm in realms:
        results["realms"][realm["id"]] = {
            "name": realm["name"],
            "id": realm["id"],
            "success": 0,
            "failed": 0,
            "agents": [],
        }

    tasks = build_task_list(realms)

    # Register persistent agent profiles on the Geister API
    register_all_agents(tasks)

    print(f"\nRunning {len(tasks)} agents across {len(realms)} realm(s)...")
    print(f"(AGENTS_COUNT={AGENTS_COUNT}/realm, MAX_WORKERS={MAX_WORKERS}, "
          f"AGENT_TIMEOUT_SECONDS={AGENT_TIMEOUT_SECONDS}, "
          f"RUN_DURATION_MINUTES={RUN_DURATION_MINUTES or 'unlimited'})")
    print("=" * 60)

    # Log persona distribution
    from collections import Counter
    persona_dist = Counter(slot.persona for _, slot, _, _ in tasks)
    for persona, count in sorted(persona_dist.items()):
        print(f"  {count:3d} × {persona}")
    print("=" * 60)

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    all_logs: List[Dict] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_meta = {
            executor.submit(run_agent_task, agent_id, slot, realm_id, realm_name): (
                agent_id, slot, realm_id, realm_name
            )
            for agent_id, slot, realm_id, realm_name in tasks
        }

        overall_deadline = time.time() + RUN_DURATION_MINUTES * 60 if RUN_DURATION_MINUTES > 0 else 0

        for future in concurrent.futures.as_completed(future_to_meta):
            if overall_deadline and time.time() > overall_deadline:
                print(f"\n⏰ Overall time limit ({RUN_DURATION_MINUTES}min) reached, skipping remaining agents...")
                break
            agent_id, slot, realm_id, realm_name = future_to_meta[future]
            log = future.result()
            all_logs.append(log)

            realm_result = results["realms"][realm_id]

            # Save per-agent log
            safe_label = slot.role_label.replace(" ", "_")
            log_file = LOGS_DIR / f"{agent_id}_{realm_name.replace(' ', '_')}_{safe_label}.json"
            with open(log_file, "w") as f:
                json.dump(log, f, indent=2)

            if log["success"]:
                realm_result["success"] += 1
                results["total_success"] += 1
                issue_count = len(log["issues"])
                issue_note = f"  ({issue_count} issue(s) found)" if issue_count else ""
                print(f"  {slot.emoji} ✅ {agent_id} [{slot.role_label}] → {realm_name}{issue_note}")
            else:
                realm_result["failed"] += 1
                results["total_failed"] += 1
                err = (log.get("error") or "unknown error")[:80]
                print(f"  {slot.emoji} ❌ {agent_id} [{slot.role_label}] → {realm_name}: {err}")

            # Update the persistent agent profile with run results
            update_agent_after_run(agent_id, log["success"], log["issues"], log.get("error"))

            realm_result["agents"].append({
                "agent_id": agent_id,
                "role_label": slot.role_label,
                "persona": slot.persona,
                "success": log["success"],
                "issues": log["issues"],
            })

            # Accumulate issues
            for issue_text in log["issues"]:
                results["total_issues"] += 1
                issue_entry = {
                    "agent_id": agent_id,
                    "role_label": slot.role_label,
                    "realm_name": realm_name,
                    "realm_id": realm_id,
                    "description": issue_text,
                    "log_file": str(log_file),
                }
                results["all_issues"].append(issue_entry)

    # --- Retry failed agents sequentially ---
    _RETRYABLE = ("524", "timeout", "timed out", "connection", "502", "503", "504")

    for retry_round in range(1, MAX_RETRIES + 1):
        failed_entries = [
            (log_entry, meta)
            for log_entry, meta in zip(all_logs, [(l["agent_id"], next(s for a, s, r, rn in tasks if a == l["agent_id"]), l["realm_id"], l["realm_name"]) for l in all_logs])
            if not log_entry["success"]
            and log_entry.get("error")
            and any(tok in log_entry["error"].lower() for tok in _RETRYABLE)
        ]
        if not failed_entries:
            break

        print(f"\n🔄 Retry round {retry_round}/{MAX_RETRIES}: {len(failed_entries)} agent(s) with transient errors")

        if overall_deadline and time.time() > overall_deadline:
            print(f"  ⏰ Time limit reached, skipping retries")
            break

        for log_entry, (agent_id, slot, realm_id, realm_name) in failed_entries:
            if overall_deadline and time.time() > overall_deadline:
                break

            time.sleep(RETRY_DELAY_SECONDS)
            print(f"  🔄 Retrying {agent_id} [{slot.role_label}] → {realm_name}...")
            new_log = run_agent_task(agent_id, slot, realm_id, realm_name)

            # Save retry log
            safe_label = slot.role_label.replace(" ", "_")
            log_file = LOGS_DIR / f"{agent_id}_{realm_name.replace(' ', '_')}_{safe_label}_retry{retry_round}.json"
            with open(log_file, "w") as f:
                json.dump(new_log, f, indent=2)

            realm_result = results["realms"][realm_id]

            if new_log["success"]:
                # Flip from failed to success
                log_entry["success"] = True
                log_entry["error"] = None
                log_entry["issues"] = new_log["issues"]
                log_entry["parsed_response"] = new_log["parsed_response"]
                realm_result["success"] += 1
                realm_result["failed"] -= 1
                results["total_success"] += 1
                results["total_failed"] -= 1
                issue_count = len(new_log["issues"])
                issue_note = f"  ({issue_count} issue(s) found)" if issue_count else ""
                print(f"  {slot.emoji} ✅ {agent_id} [{slot.role_label}] → {realm_name}{issue_note} (retry {retry_round})")

                update_agent_after_run(agent_id, True, new_log["issues"], None)

                for issue_text in new_log["issues"]:
                    results["total_issues"] += 1
                    results["all_issues"].append({
                        "agent_id": agent_id,
                        "role_label": slot.role_label,
                        "realm_name": realm_name,
                        "realm_id": realm_id,
                        "description": issue_text,
                        "log_file": str(log_file),
                    })
            else:
                err = (new_log.get("error") or "unknown error")[:80]
                print(f"  {slot.emoji} ❌ {agent_id} [{slot.role_label}] → {realm_name}: {err} (retry {retry_round})")
                # Update error in original log so next retry round sees fresh error
                log_entry["error"] = new_log.get("error")

    # Save combined log
    combined = LOGS_DIR / "all_agents.json"
    with open(combined, "w") as f:
        json.dump(all_logs, f, indent=2)
    print(f"\n📋 Agent logs saved to {LOGS_DIR}/")

    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_summary(results: Dict) -> None:
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for realm_id, realm in results["realms"].items():
        total = realm["success"] + realm["failed"]
        pct = 100 * realm["success"] / total if total > 0 else 0
        print(f"  {realm['name']}: {realm['success']}/{total} successful ({pct:.0f}%)")

    total = results["total_success"] + results["total_failed"]
    if total > 0:
        pct = 100 * results["total_success"] / total
        print(f"\n  TOTAL: {results['total_success']}/{total} successful ({pct:.1f}%)")
    else:
        print("\n  TOTAL: No agents ran")

    issue_count = results["total_issues"]
    if issue_count:
        print(f"\n  ⚠️  {issue_count} issue(s) reported by agents:")
        for i, issue in enumerate(results["all_issues"], 1):
            print(f"    {i}. [{issue['realm_name']} / {issue['role_label']}] {issue['description']}")
    else:
        print("\n  ✅ No issues reported by agents")


def write_issues_report(results: Dict) -> Path:
    """Write a human-readable issues-report.md file."""
    report_path = LOGS_DIR / "issues-report.md"
    lines = ["# Agent Swarm Issues Report\n"]
    lines.append(f"**Run:** {datetime.now().isoformat()}\n")
    lines.append(f"**Run ID:** {RUN_ID}\n")
    lines.append(f"**Network:** {NETWORK}\n")
    lines.append(f"**Agents:** {results['total_success'] + results['total_failed']}\n\n")

    if results["all_issues"]:
        lines.append(f"## Issues Found ({results['total_issues']})\n\n")
        for i, issue in enumerate(results["all_issues"], 1):
            lines.append(
                f"### Issue {i}: {issue['description']}\n"
                f"- **Realm:** {issue['realm_name']} (`{issue['realm_id']}`)\n"
                f"- **Agent:** {issue['agent_id']} ({issue['role_label']})\n"
                f"- **Log:** `{issue['log_file']}`\n\n"
            )
    else:
        lines.append("## No issues found ✅\n")

    with open(report_path, "w") as f:
        f.writelines(lines)

    print(f"📄 Issues report saved to {report_path}")
    return report_path


def file_discovered_issues(results: Dict) -> int:
    """
    File a GitHub issue for each agent-reported issue.
    Returns the number of issues successfully filed.
    """
    if not results["all_issues"]:
        return 0

    if not GITHUB_REPOSITORY or not GH_TOKEN:
        print("\n⚠️  GitHub issue filing skipped (set GITHUB_REPOSITORY and GH_TOKEN/GITHUB_TOKEN to enable)")
        return 0

    print(f"\n📝 Filing {len(results['all_issues'])} GitHub issue(s)...")
    filed = 0
    for issue in results["all_issues"]:
        title = f"[{issue['realm_name']}] {issue['description']}"

        # Load agent log for the body
        try:
            with open(issue["log_file"]) as f:
                log_data = json.load(f)
            response_text = (log_data.get("parsed_response") or {}).get("response", "")
            body = (
                f"**Discovered by agent swarm** during post-deployment staging test.\n\n"
                f"**Realm:** {issue['realm_name']} (`{issue['realm_id']}`)\n"
                f"**Agent:** {issue['agent_id']} (persona: `{issue['role_label']}`)\n"
                f"**Network:** {NETWORK}\n\n"
                f"---\n\n"
                f"**Issue reported:**\n> {issue['description']}\n\n"
                f"**Full agent response:**\n```\n{response_text[:10000]}\n```\n"
            )
        except Exception as e:
            body = (
                f"**Discovered by agent swarm** during post-deployment staging test.\n\n"
                f"**Realm:** {issue['realm_name']} (`{issue['realm_id']}`)\n"
                f"**Agent:** {issue['agent_id']} (persona: `{issue['role_label']}`)\n"
                f"**Network:** {NETWORK}\n\n"
                f"**Issue reported:**\n> {issue['description']}\n\n"
                f"_(Could not load agent log: {e})_\n"
            )

        if file_github_issue(title, body):
            filed += 1

    return filed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("GEISTER AGENT SWARM TEST")
    print("=" * 60)
    print(f"API URL:          {GEISTER_API_URL}")
    print(f"Network:          {NETWORK}")
    print(f"Run ID:           {RUN_ID}")
    print(f"Agents:           {AGENTS_COUNT}/realm")
    print(f"Timeout/agent:    {AGENT_TIMEOUT_SECONDS}s")
    dur = f"{RUN_DURATION_MINUTES}min" if RUN_DURATION_MINUTES > 0 else "unlimited"
    print(f"Overall budget:   {dur}")
    print(f"GH issue filing:  {'enabled' if GITHUB_REPOSITORY and GH_TOKEN else 'disabled'}")

    # Discover realms
    realms = discover_realms()
    if not realms:
        print("\n❌ No realms found in registry")
        sys.exit(1)

    print(f"\nFound {len(realms)} realm(s):")
    for realm in realms:
        print(f"  - {realm['name']} ({realm['id']})")

    # Run swarm
    results = run_agent_swarm(realms)

    # Print summary
    print_summary(results)

    # Write issues report artifact
    write_issues_report(results)

    # File GitHub issues for discovered problems
    gh_filed = file_discovered_issues(results)
    if gh_filed:
        print(f"\n✅ Filed {gh_filed} GitHub issue(s)")

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
