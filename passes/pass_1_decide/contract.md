# PASS 1 — DECIDE (Contract)

## Goal
Сформировать архитектуру задачи и необратимые решения для текущего job.
Результат PASS 1 становится источником правды для PASS 2–4.

## Inputs
- state.input (mode, payload, constraints)
- state.meta
- (optional) внешние правила проекта из docs/conventions.md

## Output (must produce)
- architecture_decision_json (далее: ARCH_DECISION_JSON)
- decision: "DECIDE" | "BLOCK"
- rationale_summary: кратко, без воды
- assumptions: только если неизбежно, помечать явно
- open_questions: список вопросов пользователю, если decision="BLOCK"

## Hard constraints
- НЕЛЬЗЯ выполнять задачу (никакой детализации результата).
- НЕЛЬЗЯ генерировать финальный артефакт.
- НЕЛЬЗЯ менять scope после фиксации решений.
- НЕЛЬЗЯ ссылаться на “внутреннюю память” или прошлые состояния вне state.

## Decision rules
- decision="DECIDE" если:
  - вход достаточен для формулирования архитектуры
  - риски контролируемы
  - критерии успеха определены
- decision="BLOCK" если:
  - не хватает ключевых вводных (формат результата, ограничения, критерии)
  - высокий риск неверной архитектуры
  - конфликт ограничений

## Must include in ARCH_DECISION_JSON
- pass: "DECIDE"
- immutable_snapshot: { status: "LOCKED" | "UNLOCKED", reason }
- scope:
  - what_in: что входит
  - what_out: что исключено
- output_spec:
  - artifact_types (текст/таблица/json/etc.)
  - formatting_rules
- verification_plan:
  - what_verify (что проверяет PASS 3)
  - failure_conditions (когда FAIL)
- patch_policy:
  - allowed_changes (что можно править в PASS 4)
  - forbidden_changes (что нельзя)
- risk_register:
  - top_risks (max 5)
  - mitigations

## Stop condition
PASS 1 завершён, когда:
- decision="DECIDE" и ARCH_DECISION_JSON сформирован
или
- decision="BLOCK" и open_questions сформирован

## State updates
- записать ARCH_DECISION_JSON в state.passes.decide.architecture_decision_json
- если decision="DECIDE": подготовить immutable_snapshot к LOCK (hash заполняется оркестратором)
