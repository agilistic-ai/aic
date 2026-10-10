# Chapter 10 application smoke report

Clean ZIP installation tested on October 3, 2026 with Python 3.12 on Linux. Extracted into a fresh directory and installed with `uv sync --locked --no-editable`. Every installed Python module matched the archived source. No earlier chapter checkout was required.

**14 tests passed; 0 skipped.** The suite combines controlled boundary tests and installed-application smoke tests. README describes the exact external-service boundary exercised. Model/agent/service outputs are fixtures, not live inference or real external actions. These checks establish application assembly and controls, not model quality, external account access, or production readiness.

The ZIP contains application source, fixtures, instructions and dependency metadata. It excludes installed third-party packages, virtual environments, credentials and model weights. This report was added after the clean run; the tested files remained unchanged.

```text
test_01_stable_identity_and_changed_body (test_controls.Checks.test_01_stable_identity_and_changed_body) ... ok
test_02_concurrent_duplicate_submission (test_controls.Checks.test_02_concurrent_duplicate_submission) ... ok
test_03_allowance_rejection_is_atomic (test_controls.Checks.test_03_allowance_rejection_is_atomic) ... ok
test_04_ownership_and_revocation (test_controls.Checks.test_04_ownership_and_revocation) ... ok
test_05_bounded_restart_state (test_controls.Checks.test_05_bounded_restart_state) ... ok
test_06_postcommit_recovery_keeps_receipt (test_controls.Checks.test_06_postcommit_recovery_keeps_receipt) ... ok
test_07_exact_and_repeated_approval (test_controls.Checks.test_07_exact_and_repeated_approval) ... ok
test_08_saved_answer_withheld_after_change (test_controls.Checks.test_08_saved_answer_withheld_after_change) ... ok
test_09_worker_booking_skips_embeddings_and_binds_release (test_controls.Checks.test_09_worker_booking_skips_embeddings_and_binds_release) ... ok
test_10_backup_is_recoverable_and_exclusive (test_controls.Checks.test_10_backup_is_recoverable_and_exclusive) ... ok
test_11_child_retains_worker_lock (test_controls.Checks.test_11_child_retains_worker_lock) ... ok
test_12_api_shapes_and_private_token (test_controls.Checks.test_12_api_shapes_and_private_token) ... ok
test_actual_graph_recovery_after_commit_before_checkpoint (test_runtime.RuntimeTests.test_actual_graph_recovery_after_commit_before_checkpoint) ... ok
test_complete_service_cli_restart_approval_permissions_and_backup (test_runtime.RuntimeTests.test_complete_service_cli_restart_approval_permissions_and_backup) ... ok

----------------------------------------------------------------------
Ran 14 tests in 23.999s

OK
```

---

Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved

Licensed under the [MIT License](LICENSE.txt). Provided without warranty; use at your own risk. See the [disclaimer](DISCLAIMER.md).
