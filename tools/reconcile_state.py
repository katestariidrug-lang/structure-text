#!/usr/bin/env python3
import json
import sys
from datetime import datetime, timezone

PHASE_ORDER = ["DECIDE", "EXECUTE", "VERIFY", "PATCH", "DONE"]

def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def compute_phase(passes: dict) -> str:
    # Canon: next not-run pass after last PASS
    decide = passes.get("decide", {}).get("status")
    execute = passes.get("execute", {}).get("status")
    verify = passes.get("verify", {}).get("status")
    patch = passes.get("patch", {}).get("status")

    if decide != "PASS":
        return "DECIDE"
    if execute != "PASS":
        return "EXECUTE"
    # execute is PASS here
    if verify == "PASS":
        return "DONE"
    if verify in ("FAIL", "ERROR"):
        return "PATCH"
    # NOT_RUN / PENDING / missing
    return "VERIFY"

def compute_run_state(passes: dict, phase: str) -> str:
    # Keep it simple: if phase is DONE -> IDLE, else READY
    if phase == "DONE":
        return "IDLE"
    return "READY"

def main():
    if len(sys.argv) < 2:
        print("Usage: reconcile_state.py <state.json> [--check]")
        sys.exit(2)

    path = sys.argv[1]
    check_only = "--check" in sys.argv[2:]

    with open(path, "r", encoding="utf-8") as f:
        state = json.load(f)

    passes = state.get("passes", {})
    new_phase = compute_phase(passes)
    new_run_state = compute_run_state(passes, new_phase)

    status = state.setdefault("status", {})
    changed = False

    if status.get("phase") != new_phase:
        status["phase"] = new_phase
        changed = True
    if status.get("run_state") != new_run_state:
        status["run_state"] = new_run_state
        changed = True

    status["last_updated_at"] = now_iso()

    if check_only:
        if changed:
            print(f"NEEDS_UPDATE phase={status.get('phase')} run_state={status.get('run_state')}")
            sys.exit(1)
        print("OK")
        sys.exit(0)

    if changed:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"UPDATED phase={new_phase} run_state={new_run_state}")
    else:
        print("NO_CHANGES")

if __name__ == "__main__":
    main()
