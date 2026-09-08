"""The in-process exemption list may only shrink.

``"runtime": "in_process"`` documents that an extension still needs full host
privilege — it is a debt marker, not a feature. Without something holding the
line, adding one more exemption is always easier than porting an extension to
the capability bridge, and the trusted set grows instead of shrinking.

``scripts/sandbox_exemptions.json`` pins the set. This test fails when:

  - an extension outside the baseline declares in_process, or imports host
    modules it would need an exemption for (new debt);
  - a baseline entry no longer imports host modules (debt already paid — the
    entry has to go, so the count reflects reality).

The last case is why porting an extension is not complete until its baseline
entry is deleted.
"""

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "declare_extension_runtime.py"


def _ratchet():
    spec = importlib.util.spec_from_file_location("declare_extension_runtime", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def ratchet():
    if not SCRIPT.exists():
        pytest.skip("ratchet script not present")
    module = _ratchet()
    if not Path(module.DEFAULT_EXTENSIONS_DIR).is_dir():
        pytest.skip("extensions submodule not checked out")
    return module


def test_exemption_list_only_shrinks(ratchet):
    problems = ratchet.check()
    assert not problems, "sandbox exemption ratchet violated:\n" + "\n".join(
        f"  - {p}" for p in problems
    )


def test_every_exemption_has_a_tracking_issue(ratchet):
    """An exemption nobody has filed an issue for is an exemption nobody owns.

    Keeping the two lists in step is what makes "the ratchet count" a real
    number rather than a description: it is also the number of open ports.
    """
    import json

    data = json.loads(
        (REPO_ROOT / "scripts" / "sandbox_exemptions.json").read_text()
    )
    exempt = set(data["exempt"])
    tracked = set(data.get("tracking_issues", {}))

    assert not exempt - tracked, (
        f"exemptions with no tracking issue: {sorted(exempt - tracked)}. "
        "File one, or delete the exemption."
    )
    assert not tracked - exempt, (
        f"tracking issues for extensions that are no longer exempt: "
        f"{sorted(tracked - exempt)}. Close them and remove the entries."
    )


def test_backend_grant_list_matches_the_baseline():
    """The canister must grant privilege to exactly the audited set.

    ``scripts/sandbox_exemptions.json`` is a repo file and is not packed into the
    WASM, so the backend carries its own copy in
    ``core.privileged_extensions``. If the two drift, the ratchet stops
    describing what the deployed canister actually trusts.
    """
    import json
    import sys

    sys.path.insert(0, str(REPO_ROOT / "src" / "realm_backend"))
    from core.privileged_extensions import IN_PROCESS_EXEMPT_EXTENSION_IDS

    baseline = set(
        json.loads((REPO_ROOT / "scripts" / "sandbox_exemptions.json").read_text())[
            "exempt"
        ]
    )
    assert set(IN_PROCESS_EXEMPT_EXTENSION_IDS) == baseline, (
        "core/privileged_extensions.py and scripts/sandbox_exemptions.json "
        "disagree about which non-core extensions may run in-process"
    )


def test_manifest_cannot_grant_itself_host_access():
    """A package requesting in_process gets it only if the host already trusts it."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "src" / "realm_backend"))
    from core.privileged_extensions import may_run_in_process

    assert may_run_in_process("demo_simulator") is True  # audited exemption
    assert may_run_in_process("public_dashboard") is True  # core
    for untrusted in ("attacker_ext", "hello_world", "", "member_dashboard_evil"):
        assert may_run_in_process(untrusted) is False, (
            f"{untrusted!r} must not receive host privilege; in_process is "
            "granted by the host list, not requested by the package"
        )


def test_progress_is_visible(ratchet):
    """Surface the remaining count so the number moves in review, not silently."""
    state = ratchet.survey()
    remaining = sorted(e for e, i in state.items() if i["imports"])
    clean = sorted(e for e, i in state.items() if not i["imports"])
    print(
        f"\nnon-core extensions still in-process: {len(remaining)}"
        f" | sandbox-clean: {len(clean)}"
    )
    assert len(remaining) == len(ratchet.load_baseline()), (
        "baseline size and measured in-process count disagree; "
        "run scripts/declare_extension_runtime.py --check for detail"
    )
