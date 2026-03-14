# Functional Regression Plan

## Goal
Automate the full `B2C GB` checklist (203 rows in Excel) without creating 203 isolated UI tests.

## Constraints
- Stack: Python 3.12, `pytest`, Playwright sync API, Allure.
- Existing architecture must be preserved:
  - `tests/` = thin orchestration + asserts
  - `flows/` = business journeys
  - `pages/` = page-level actions/selectors
  - `utils/` = APIs/retries/helpers
- CI executes through `.github/workflows/e2e.yml` and GitHub secrets.

## Strategy
1. Keep one source of truth for checklist rows:
   - extract Excel rows to `data/regression/b2c_gb_cases.json` (and CSV).
2. Group rows into reusable functional modules:
   - use `data/regression/functional_groups.yaml`.
3. Build parametrized tests per module, not per row:
   - one test function can cover many checklist IDs.
4. Track explicit coverage mapping:
   - every automated scenario declares `covers_case_ids`.
   - generate coverage report (`covered / uncovered`) on each CI run.

## Proposed Test Modules
1. `test_functional_site_shell.py`
2. `test_functional_discovery.py`
3. `test_functional_pdp.py`
4. `test_functional_basket.py`
5. `test_functional_checkout.py`
6. `test_functional_payment_matrix.py`
7. `test_functional_order_lifecycle.py`
8. `test_functional_comms_support.py`

This usually lands around 20-35 parametrized scenarios, each mapped to multiple checklist rows.

## Existing Reusable Assets
- Checkout/payment/order flows already exist in `flows/purchase_flow.py`.
- Persona/payment coverage exists in `tests/ui/*` and can be reused as the base for the functional matrix.
- Shipment and retry logic exists in `utils/shipment_api.py`.

## Immediate Next Steps
1. Run extractor on each checklist update:
   - `python tools/extract_b2c_cases.py --xlsx /path/to/Py_Test_Regex.xlsx --summary`
2. Create `tests/functional/` with the first module:
   - start from `checkout_core` + `payment_matrix`.
3. Add coverage metadata file:
   - `data/regression/automation_coverage.yaml` with `case_id -> automated_by`.
4. Add CI gate:
   - fail if a `High` priority case is marked automated but has no linked test id.

## Definition of Done
- Checklist is fully mapped (`203/203` rows have coverage status).
- `High` priority rows are fully automated and green in CI.
- Functional tests are stable and grouped by business capability, not by single row count.
