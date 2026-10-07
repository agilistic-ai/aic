# Chapter 7 application smoke report

Clean ZIP installation tested on October 3, 2026 with Python 3.12 on Linux. Extracted into a fresh directory and installed with `uv sync --locked --no-editable`. Every installed Python module matched the archived source. No earlier chapter checkout was required.

**11 tests passed; 1 skipped (browser runtime unavailable).** The suite combines controlled boundary tests and installed-application smoke tests. README describes the exact external-service boundary exercised. Model/agent/service outputs are fixtures, not live inference or real external actions. These checks establish application assembly and controls, not model quality, external account access, or production readiness.

The ZIP contains application source, fixtures, instructions and dependency metadata. It excludes installed third-party packages, virtual environments, credentials and model weights. This report was added after the clean run; the tested files remained unchanged.

```text
test_01_static_fetch_and_dynamic_gap (test_controls.Checks.test_01_static_fetch_and_dynamic_gap) ... ok
test_02_source_scope_and_budget (test_controls.Checks.test_02_source_scope_and_budget) ... ok
test_03_bad_citations (test_controls.Checks.test_03_bad_citations) ... ok
test_04_semantic_error_still_requires_review (test_controls.Checks.test_04_semantic_error_still_requires_review) ... ok
test_05_baseline_and_wording_change_suppress_alerts (test_controls.Checks.test_05_baseline_and_wording_change_suppress_alerts) ... ok
test_06_changed_price_and_duplicate_run (test_controls.Checks.test_06_changed_price_and_duplicate_run) ... ok
test_07_conflict_and_missing_coverage (test_controls.Checks.test_07_conflict_and_missing_coverage) ... ok
test_08_late_run_does_not_regress_baseline (test_controls.Checks.test_08_late_run_does_not_regress_baseline) ... ok
test_09_notification_recovery (test_controls.Checks.test_09_notification_recovery) ... ok
test_10_changed_scope_is_rejected (test_controls.Checks.test_10_changed_scope_is_rejected) ... ok
test_real_browser_exposes_dynamic_offer (test_runtime.BrowserSmoke.test_real_browser_exposes_dynamic_offer) ... skipped 'Set AIC_BROWSER_SMOKE=1 on a host with installed sandboxed Chromium.'
test_actual_agent_both_provider_integrations_and_monitoring (test_runtime.RuntimeTests.test_actual_agent_both_provider_integrations_and_monitoring) ... ok

----------------------------------------------------------------------
Ran 12 tests in 18.246s

OK (skipped=1)
```
