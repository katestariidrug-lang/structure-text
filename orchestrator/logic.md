# Orchestrator Logic — 4-pass LLM Workflow

## Purpose
This document defines the deterministic execution rules of the 4-pass workflow:
DECIDE → EXECUTE → VERIFY → PATCH

The orchestrator is the only component allowed to:
- advance workflow phases
- lock immutable decisions
- stop execution
- mark the job as DONE or BLOCKED

LLM has NO authority over flow control.

---

## Global Principles

1. LLM is a pure function: input → output
2. State is the single source of truth
3. No pass can modify results of previous passes
4. Any violation of preconditions results in STOP
5. Human intervention is allowed ONLY via state update or job restart

---

## Workflow Phases Overview

| Phase | Pass | Can run if | Can produce |
|-----|-----|-----------|-------------|
| DECIDE | PASS 1 | job created | ARCH_DECISION_JSON |
| EXECUTE | PASS 2 | immutable_snapshot = LOCKED | artifact |
| VERIFY | PASS 3 | artifact exists | issues |
| PATCH | PASS 4 | issues exist | patched_artifact |
| DONE | — | no BLOCKER issues | final output |

---

## PASS 1 — DECIDE

### Preconditions
- state.status.phase = DECIDE
- state.passes.decide.status = NOT_RUN

### Execution
- Run PASS 1 prompt
- Capture output

### Postconditions
- If decision = BLOCK:
  - state.status.run_state = BLOCKED
  - state.status.phase = DECIDE
  - STOP workflow
- If decision = DECIDE:
  - write architecture_decision_json to state
  - set immutable_snapshot.status = LOCKED
  - calculate immutable_snapshot.hash (outside LLM)
  - advance phase → EXECUTE

---

## PASS 2 — EXECUTE

### Preconditions
- state.status.phase = EXECUTE
- immutable_snapshot.status = LOCKED
- architecture_decision_json exists

### Execution
- Run PASS 2 prompt
- Capture artifact

### Postconditions
- If PASS 2 fails:
  - state.status.run_state = BLOCKED
  - STOP workflow
- If PASS 2 succeeds:
  - persist artifact to jobs/{job_id}/output
  - advance phase → VERIFY

---

## PASS 3 — VERIFY

### Preconditions
- state.status.phase = VERIFY
- artifact exists
- architecture_decision_json exists

### Execution
- Run PASS 3 prompt
- Capture issues list

### Postconditions
- If BLOCKER issues exist:
  - advance phase → PATCH
- If no BLOCKER issues:
  - state.status.phase = DONE
  - state.status.run_state = COMPLETED
  - STOP workflow (successful completion)

---

## PASS 4 — PATCH

### Preconditions
- state.status.phase = PATCH
- issues list exists
- at least one issue with severity BLOCKER or MAJOR

### Execution
- Run PASS 4 prompt
- Capture patched_artifact and patch_plan

### Postconditions
- Persist patched_artifact as final output
- state.status.phase = DONE
- state.status.run_state = COMPLETED

---

## Forbidden Transitions

- EXECUTE before DECIDE
- VERIFY before EXECUTE
- PATCH before VERIFY
- Any pass re-run without explicit state reset
- Any modification of immutable_snapshot after LOCK

Any forbidden transition → HARD STOP.

---

## Restart Policy

A job may be restarted ONLY by:
- creating a new job_id
- or explicitly resetting state to DECIDE with immutable_snapshot cleared

Partial reruns are forbidden.

---

## Completion Criteria

A job is considered DONE if:
- state.status.phase = DONE
- state.status.run_state = COMPLETED
- final output exists
- immutable_snapshot remains unchanged since PASS 1

---

## Auditability

At any point, it must be possible to answer:
- What decisions were made?
- When were they locked?
- Which issues were found?
- Which fixes were applied and why?

If this cannot be reconstructed from state + jobs folder → system is broken.
