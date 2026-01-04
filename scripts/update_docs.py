#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Structure-Text Orchestrator: deterministic docs updater.

Source of truth: jobs/<job_id>/state/state.json

Updates:
- README.md: replaces only AUTOGEN block STATE_SUMMARY
- jobs/<job_id>/STATUS.md: fully regenerates
- CHANGELOG.md: untouched unless --bump YYYY-MM-DD is provided (then prepends entry into AUTOGEN block CHANGELOG)

Usage:
  python scripts/update_docs.py --state jobs/job_0002/state/state.json
  python scripts/update_docs.py --state jobs/job_0002/state/state.json --bump 2026-01-04
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


# ----------------------------
# Helpers
# ----------------------------

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def replace_autogen_block(text: str, tag: str, new_block: str) -> str:
    """
    Replace content between:
      <!-- AUTOGEN:BEGIN {tag} -->
      ...
      <!-- AUTOGEN:END {tag} -->
    """
    begin = f"<!-- AUTOGEN:BEGIN {tag} -->"
    end = f"<!-- AUTOGEN:END {tag} -->"

    if begin not in text or end not in text:
        raise RuntimeError(
            f"Missing autogen markers for tag '{tag}'. "
            f"Add {begin} and {end} to the file first."
        )

    pre, rest = text.split(begin, 1)
    _, post = rest.split(end, 1)

    return pre + begin + "\n" + new_block.rstrip() + "\n" + end + post


def extract_autogen_block(text: str, tag: str) -> str:
    begin = f"<!-- AUTOGEN:BEGIN {tag} -->"
    end = f"<!-- AUTOGEN:END {tag} -->"
    if begin not in text or end not in text:
        raise RuntimeError(f"Missing autogen markers for tag '{tag}'.")
    _, rest = text.split(begin, 1)
    block, _ = rest.split(end, 1)
    return block


# ----------------------------
# State summary model
# ----------------------------

@dataclass(frozen=True)
class PassSummary:
    name: str
    status: str
    started_at: str
    ended_at: str
    errors_count: int
    issues_count: Optional[int] = None


@dataclass(frozen=True)
class JobSummary:
    job_id: str
    schema_version: str
    created_at: str
    last_updated_at: str
    phase: str
    run_state: str
    immutable_status: str
    immutable_hash: str
    execute_artifact_ref: str
    verify_issue_counts: Dict[str, int]
    passes: List[PassSummary]


def compute_verify_issue_counts(state: Dict[str, Any]) -> Dict[str, int]:
    issues = (((state.get("passes") or {}).get("verify") or {}).get("issues")) or []
    counts = {"BLOCKER": 0, "MAJOR": 0, "MINOR": 0}
    for it in issues:
        sev = (it or {}).get("severity")
        if sev in counts:
            counts[sev] += 1
    return counts


def build_summary(state: Dict[str, Any]) -> JobSummary:
    meta = state.get("meta") or {}
    status = state.get("status") or {}
    passes = state.get("passes") or {}
    immutable = state.get("immutable_snapshot") or {}

    job_id = str(meta.get("job_id") or "")
    schema_version = str(meta.get("schema_version") or "")
    created_at = str(meta.get("created_at") or "")
    last_updated_at = str(status.get("last_updated_at") or "")
    phase = str(status.get("phase") or "")
    run_state = str(status.get("run_state") or "")

    immutable_status = str(immutable.get("status") or "")
    immutable_hash = str(immutable.get("hash") or "")

    execute_artifact_ref = str((((passes.get("execute") or {}).get("result") or {}).get("artifact_ref")) or "")

    verify_issue_counts = compute_verify_issue_counts(state)

    order = ["decide", "execute", "verify", "patch"]
    ps: List[PassSummary] = []
    for name in order:
        pobj = passes.get(name) or {}
        pstatus = str(pobj.get("status") or "NOT_RUN")
        started_at = str(pobj.get("started_at") or "")
        ended_at = str(pobj.get("ended_at") or "")
        errors_count = len(pobj.get("errors") or [])
        issues_count = None
        if name == "verify":
            issues_count = len(pobj.get("issues") or [])
        ps.append(PassSummary(
            name=name,
            status=pstatus,
            started_at=started_at,
            ended_at=ended_at,
            errors_count=errors_count,
            issues_count=issues_count
        ))

    return JobSummary(
        job_id=job_id,
        schema_version=schema_version,
        created_at=created_at,
        last_updated_at=last_updated_at,
        phase=phase,
        run_state=run_state,
        immutable_status=immutable_status,
        immutable_hash=immutable_hash,
        execute_artifact_ref=execute_artifact_ref,
        verify_issue_counts=verify_issue_counts,
        passes=ps,
    )


# ----------------------------
# Renderers
# ----------------------------

def render_readme_state_summary(s: JobSummary) -> str:
    locked = "LOCKED" if s.immutable_status == "LOCKED" else s.immutable_status or "UNKNOWN"
    issues_total = sum(s.verify_issue_counts.values())

    lines: List[str] = []
    lines.append("### Текущее состояние проекта (автоген из state.json)")
    lines.append("")
    lines.append(f"- Канонический job: **{s.job_id}**")
    if s.schema_version:
        lines.append(f"- schema_version: `{s.schema_version}`")
    if s.created_at:
        lines.append(f"- created_at: `{s.created_at}`")
    if s.last_updated_at:
        lines.append(f"- last_updated_at: `{s.last_updated_at}`")
    lines.append(f"- immutable_snapshot: **{locked}**" + (f" (hash: `{s.immutable_hash}`)" if s.immutable_hash else ""))
    lines.append(f"- status: phase=`{s.phase}`, run_state=`{s.run_state}`")
    lines.append("")
    lines.append("### PASS статус")
    lines.append("")
    lines.append("| PASS | status | started_at | ended_at | errors | notes |")
    lines.append("|---|---|---|---|---:|---|")
    for p in s.passes:
        note = ""
        if p.name == "execute" and s.execute_artifact_ref:
            note = f"artifact_ref={s.execute_artifact_ref}"
        if p.name == "verify":
            note = f"issues={p.issues_count}"
        lines.append(
            f"| {p.name} | {p.status} | {p.started_at} | {p.ended_at} | {p.errors_count} | {note} |"
        )
    lines.append("")
    lines.append("### VERIFY issues (по severity)")
    lines.append("")
    lines.append(f"- BLOCKER: **{s.verify_issue_counts.get('BLOCKER', 0)}**")
    lines.append(f"- MAJOR: **{s.verify_issue_counts.get('MAJOR', 0)}**")
    lines.append(f"- MINOR: **{s.verify_issue_counts.get('MINOR', 0)}**")
    lines.append(f"- issues_total: **{issues_total}**")
    lines.append("")
    lines.append("### Как обновить документацию")
    lines.append("")
    lines.append("```bash")
    lines.append(f"python scripts/update_docs.py --state jobs/{s.job_id}/state/state.json")
    lines.append("```")
    return "\n".join(lines)


def render_status_md(s: JobSummary, state_rel_path: str) -> str:
    locked = "LOCKED" if s.immutable_status == "LOCKED" else s.immutable_status or "UNKNOWN"
    issues_total = sum(s.verify_issue_counts.values())

    def find_pass(name: str) -> PassSummary:
        for p in s.passes:
            if p.name == name:
                return p
        return PassSummary(name=name, status="NOT_RUN", started_at="", ended_at="", errors_count=0)

    pd = find_pass("decide")
    pe = find_pass("execute")
    pv = find_pass("verify")
    pp = find_pass("patch")

    lines: List[str] = []
    lines.append(f"# STATUS — {s.job_id}")
    lines.append("")
    lines.append(f"Источник истины: `{state_rel_path}`")
    lines.append("")
    lines.append("## Meta")
    lines.append(f"- job_id: `{s.job_id}`")
    if s.schema_version:
        lines.append(f"- schema_version: `{s.schema_version}`")
    if s.created_at:
        lines.append(f"- created_at: `{s.created_at}`")
    if s.last_updated_at:
        lines.append(f"- last_updated_at: `{s.last_updated_at}`")
    lines.append(f"- phase: `{s.phase}`")
    lines.append(f"- run_state: `{s.run_state}`")
    lines.append("")
    lines.append("## Immutable snapshot")
    lines.append(f"- status: `{locked}`" + (f", hash: `{s.immutable_hash}`" if s.immutable_hash else ""))
    lines.append("")
    lines.append("## PASS статус")
    lines.append("")
    lines.append("| PASS | status | started_at | ended_at | errors |")
    lines.append("|---|---|---|---|---:|")
    lines.append(f"| DECIDE | {pd.status} | {pd.started_at} | {pd.ended_at} | {pd.errors_count} |")
    lines.append(f"| EXECUTE | {pe.status} | {pe.started_at} | {pe.ended_at} | {pe.errors_count} |")
    lines.append(f"| VERIFY | {pv.status} | {pv.started_at} | {pv.ended_at} | {pv.errors_count} |")
    lines.append(f"| PATCH | {pp.status} | {pp.started_at} | {pp.ended_at} | {pp.errors_count} |")
    lines.append("")
    lines.append("## Артефакты")
    lines.append(f"- PASS 2 (EXECUTE) artifact_ref: `{s.execute_artifact_ref}`" if s.execute_artifact_ref else "- PASS 2 (EXECUTE) artifact_ref: (empty)")
    lines.append("")
    lines.append("## VERIFY issues")
    lines.append(f"- BLOCKER: {s.verify_issue_counts.get('BLOCKER', 0)}")
    lines.append(f"- MAJOR: {s.verify_issue_counts.get('MAJOR', 0)}")
    lines.append(f"- MINOR: {s.verify_issue_counts.get('MINOR', 0)}")
    lines.append(f"- issues_total: {issues_total}")
    lines.append("")
    lines.append("## PATCH")
    if issues_total == 0:
        lines.append("PATCH запрещён: issues отсутствуют (чинить нечего).")
    else:
        lines.append("PATCH допустим только по issues из VERIFY.")
    lines.append("")
    return "\n".join(lines)


def render_changelog_entry(s: JobSummary, bump_date: str) -> str:
    issues_total = sum(s.verify_issue_counts.values())
    pmap = {p.name: p.status for p in s.passes}
    p123 = f"{pmap.get('decide','')}/{pmap.get('execute','')}/{pmap.get('verify','')}"
    lines: List[str] = []
    lines.append(f"## {bump_date}")
    lines.append(f"- Авто-обновление документации по `jobs/{s.job_id}/state/state.json`.")
    lines.append(f"- Канонический job подтверждён: `{s.job_id}` (PASS1–3={p123}, issues={issues_total}).")
    return "\n".join(lines)


# ----------------------------
# Main
# ----------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True, help="Path to jobs/<job_id>/state/state.json")
    ap.add_argument("--repo-root", default=".", help="Repo root (default: .)")
    ap.add_argument("--bump", default="", help="If set (YYYY-MM-DD), prepends a new entry into CHANGELOG autogen block.")
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    state_path = (repo_root / args.state).resolve()
    if not state_path.exists():
        raise SystemExit(f"state.json not found: {state_path}")

    state = load_json(state_path)
    summary = build_summary(state)

    # README: update only STATE_SUMMARY autogen block
    readme_path = repo_root / "README.md"
    readme_text = read_text(readme_path)
    readme_new = replace_autogen_block(readme_text, "STATE_SUMMARY", render_readme_state_summary(summary))
    write_text(readme_path, readme_new)

    # STATUS: regenerate fully
    status_path = repo_root / "jobs" / summary.job_id / "STATUS.md"
    write_text(status_path, render_status_md(summary, args.state))

    # CHANGELOG: do nothing unless bump
    if args.bump:
        changelog_path = repo_root / "docs" / "CHANGELOG.md"
        if changelog_path.exists():
            ch = read_text(changelog_path)
            # Prepend entry into AUTOGEN block CHANGELOG
            existing = extract_autogen_block(ch, "CHANGELOG").strip()
            entry = render_changelog_entry(summary, args.bump).rstrip()
            combined = entry if not existing else (entry + "\n" + existing)
            ch_new = replace_autogen_block(ch, "CHANGELOG", combined)
            write_text(changelog_path, ch_new)
        else:
            raise SystemExit("docs/CHANGELOG.md not found but --bump was provided.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
