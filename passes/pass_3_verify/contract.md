# PASS 3 — VERIFY (Contract)

## Goal
Проверить артефакт PASS 2 на соответствие ARCH_DECISION_JSON и constraints.
Выдать список проблем (issues) с evidence и severity.

## Inputs
- state.passes.decide.architecture_decision_json
- artifact из PASS 2 (по ссылке output_ref)
- state.input.constraints

## Output (must produce)
- issues[]:
  - issue_id (ISSUE_0001…)
  - severity: BLOCKER | MAJOR | MINOR
  - title
  - evidence (цитата/фрагмент/точное место)
  - location (если применимо)
  - recommendation (что исправить)
- verification_summary:
  - pass/fail
  - blocker_count, major_count, minor_count

## Hard constraints
- НЕЛЬЗЯ исправлять артефакт.
- НЕЛЬЗЯ переписывать вывод PASS 2.
- НЕЛЬЗЯ добавлять требования, которых нет в ARCH_DECISION_JSON/constraints.
- Каждая проблема обязана иметь evidence.

## Severity rules
- BLOCKER: нарушает output_spec, scope, immutable_snapshot правила, или критические constraints
- MAJOR: существенное несоответствие требованиям, но не ломает формат целиком
- MINOR: косметика, стиль, небольшие уточнения

## Stop condition
PASS 3 завершён, когда:
- issues[] сформирован
- verification_summary сформирован

## State updates
- записать issues в state.passes.verify.issues
- выставить state.passes.verify.status = PASS если blocker_count=0 иначе FAIL
