# Chapter 8 application smoke report

Clean ZIP installation tested on October 3, 2026 with Python 3.12 on Linux. Extracted into a fresh directory and installed with `uv sync --locked --no-editable`. Every installed Python module matched the archived source. No earlier chapter checkout was required.

**11 tests passed; 1 skipped.** The suite combines controlled boundary tests and installed-application smoke tests. README describes the exact external-service boundary exercised. Model/agent/service outputs are fixtures, not live inference or real external actions. These checks establish application assembly and controls, not model quality, external account access, or production readiness.

The ZIP contains application source, fixtures, instructions and dependency metadata. It excludes installed third-party packages, virtual environments, credentials and model weights. This report was added after the clean run; the tested files remained unchanged.

```text
test_descendant_cannot_hold_output_pipe_past_timeout (test_cli.CliTests.test_descendant_cannot_hold_output_pipe_past_timeout) ... ok
test_installed_cli_patch_and_failed_scope (test_cli.CliTests.test_installed_cli_patch_and_failed_scope) ... ok
test_missing_docker_and_invalid_image_fail_without_launch (test_cli.CliTests.test_missing_docker_and_invalid_image_fail_without_launch) ... ok
test_real_coding_worker_and_acceptance (test_cli.ContainerSmoke.test_real_coding_worker_and_acceptance) ... skipped 'Set AIC_CODING_SMOKE_IMAGE with Docker and the isolated model service ready.'
test_01_seed_failure_and_fix (test_controls.Checks.test_01_seed_failure_and_fix) ... ok
test_02_all_authoritative_cases (test_controls.Checks.test_02_all_authoritative_cases) ... ok
test_03_scope_changes (test_controls.Checks.test_03_scope_changes) ... ok
test_04_added_file (test_controls.Checks.test_04_added_file) ... ok
test_05_symlink_and_size (test_controls.Checks.test_05_symlink_and_size) ... ok
test_06_timeout_and_output_bound (test_controls.Checks.test_06_timeout_and_output_bound) ... ok
test_07_zero_exit_without_result_fails (test_controls.Checks.test_07_zero_exit_without_result_fails) ... ok
test_08_package_and_patch_application (test_controls.Checks.test_08_package_and_patch_application) ... ok

----------------------------------------------------------------------
Ran 12 tests in 1.927s

OK (skipped=1)
```

Separate harness check (installed locked dependencies, not Docker):

```text
OpenHands 1.51.0 imports, agent/tool construction, and conversation arguments passed.
No container, tool execution, or model inference was exercised.
```

---

Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved

Licensed under the [MIT License](LICENSE.txt). Provided without warranty; use at your own risk. See the [disclaimer](DISCLAIMER.md).
