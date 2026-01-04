# PASS 2 — EXECUTE (Contract)

## Goal
Выполнить задачу строго по ARCH_DECISION_JSON, без самодеятельности.
Создать артефакт(ы) в указанном формате.

## Inputs
- state.input
- state.passes.decide.architecture_decision_json (обязательно)
- state.immutable_snapshot.status MUST be "LOCKED" (если нет — STOP)

## Output (must produce)
- artifact: финальный результат согласно output_spec
- execution_log: кратко (что сделано), без рассуждений
- deviations: если были, строго с причиной и ссылкой на constraint

## Hard constraints
- НЕЛЬЗЯ менять ARCH_DECISION_JSON.
- НЕЛЬЗЯ расширять scope.
- НЕЛЬЗЯ добавлять новые типы артефактов.
- НЕЛЬЗЯ решать вопросы, которые должны были быть в PASS 1 (архитектура).
- Если immutable_snapshot != LOCKED → FAIL (или STOP без выполнения).

## Execution rules
- следовать output_spec.formatting_rules
- соблюдать constraints из state.input.constraints
- если что-то невозможно выполнить без изменения архитектуры:
  - остановиться и вернуть FAIL + reason (не “импровизировать”)

## Stop condition
PASS 2 завершён, когда:
- artifact сформирован
- execution_log сформирован
- deviations перечислены (или пусто)

## State updates
- записать artifact в jobs/.../output (оркестратор)
- сохранить ссылки в state.passes.execute.output_ref
