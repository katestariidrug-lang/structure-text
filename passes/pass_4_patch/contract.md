# PASS 4 — PATCH (Contract)

## Goal
Внести точечные исправления в артефакт PASS 2 строго по issues из PASS 3.
Использовать patch_plan, привязанный к issue_id.

## Inputs
- artifact из PASS 2
- state.passes.verify.issues
- state.passes.decide.architecture_decision_json (patch_policy)

## Output (must produce)
- patched_artifact: исправленная версия
- patch_plan[]:
  - issue_id
  - action: SEARCH_REPLACE | INSERT | DELETE
  - target_ref (где правим)
  - payload (что вставить/на что заменить)
- patch_report:
  - fixed_issue_ids[]
  - not_fixed_issue_ids[] + reason
  - regression_risks (если есть)

## Hard constraints
- НЕЛЬЗЯ менять архитектуру.
- НЕЛЬЗЯ исправлять то, чего нет в issues.
- НЕЛЬЗЯ править BLOCKER обходными “красивыми” способами, только по сути.
- НЕЛЬЗЯ добавлять новые требования.
- Если issue не закрывается без изменения ARCH_DECISION_JSON → оставить not_fixed с причиной.

## Stop condition
PASS 4 завершён, когда:
- patched_artifact сформирован
- patch_plan сформирован
- patch_report сформирован

## State updates
- записать patch_plan в state.passes.patch.patch_plan
- сохранить patched_artifact как финальный output (оркестратор)
