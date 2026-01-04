<!--
Роль: подробная логика пайплайна (DECIDE → EXECUTE → VERIFY → PATCH).
Содержит:
- вход/выход каждого PASS (с примерами полей)
- что запрещено на каждом PASS
- зависимость “PATCH только после VERIFY”, “EXECUTE только после LOCKED”
-->

# WORKFLOW: Structure-Text Orchestrator

## PASS 1 — DECIDE
Архитектура, scope, LOCKED snapshot. Необратимые решения.

## PASS 2 — EXECUTE
Построение `structure_spec` строго по архитектуре PASS 1.

- Выход: `structure_spec` в **Strict JSON** (не Markdown)
- Артефакт фиксируется через `passes.execute.result.artifact_ref`

## PASS 3 — VERIFY
Аудит результата EXECUTE. Исправления запрещены.

- Выход: список `issues` (BLOCKER/MAJOR/MINOR)
- Issues фиксируются в `passes.verify.issues` внутри `state.json`
- Если issues пустой и BLOCKER=0 → VERIFY = PASS

## PASS 4 — PATCH
Точечные правки строго по issues VERIFY.
