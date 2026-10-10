# Chapter 6 application smoke report

Clean ZIP installation tested on October 3, 2026 with Python 3.12 on Linux. Extracted into a fresh directory and installed with `uv sync --locked --no-editable`. Every installed Python module matched the archived source. No earlier chapter checkout was required.

**15 tests passed.** The suite combines controlled boundary tests and installed-application smoke tests. README describes the exact external-service boundary exercised. Model/agent/service outputs are fixtures, not live inference or real external actions. These checks establish application assembly and controls, not model quality, external account access, or production readiness.

The ZIP contains application source, fixtures, instructions and dependency metadata. It excludes installed third-party packages, virtual environments, credentials and model weights. This report was added after the clean run; the tested files remained unchanged.

```text
test_01_complete_verified_booking (test_controls.Checks.test_01_complete_verified_booking) ... ok
test_02_recovery_after_lost_response_and_expiry (test_controls.Checks.test_02_recovery_after_lost_response_and_expiry) ... ok
test_03_expired_before_write (test_controls.Checks.test_03_expired_before_write) ... ok
test_04_changed_arguments (test_controls.Checks.test_04_changed_arguments) ... ok
test_05_request_collision (test_controls.Checks.test_05_request_collision) ... ok
test_06_wrong_actor_and_private_readback (test_controls.Checks.test_06_wrong_actor_and_private_readback) ... ok
test_07_revocation (test_controls.Checks.test_07_revocation) ... ok
test_08_stale_slot (test_controls.Checks.test_08_stale_slot) ... ok
test_09_unverified_outcome (test_controls.Checks.test_09_unverified_outcome) ... ok
test_10_two_competing_transactions (test_controls.Checks.test_10_two_competing_transactions) ... ok
test_11_loop_observed_slot (test_controls.Checks.test_11_loop_observed_slot) ... ok
test_12_loop_invented_slot_and_budget (test_controls.Checks.test_12_loop_invented_slot_and_budget) ... ok
test_actual_checkpoint_recovery_after_commit_response_loss (test_runtime.RuntimeTests.test_actual_checkpoint_recovery_after_commit_response_loss) ... ok
test_installed_cli_real_mcp_langgraph_both_sdks (test_runtime.RuntimeTests.test_installed_cli_real_mcp_langgraph_both_sdks) ... ok
test_renew_expired_approval_in_failed_perform_node (test_runtime.RuntimeTests.test_renew_expired_approval_in_failed_perform_node) ... ok

----------------------------------------------------------------------
Ran 15 tests in 17.384s

OK
```

---

Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved

Licensed under the [MIT License](LICENSE.txt). Provided without warranty; use at your own risk. See the [disclaimer](DISCLAIMER.md).
