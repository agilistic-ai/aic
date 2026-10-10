# Chapter 5 application smoke report

Clean ZIP installation tested on October 3, 2026 with Python 3.12 on Linux. Extracted into a fresh directory and installed with `uv sync --locked --no-editable`. Every installed Python module matched the archived source. No earlier chapter checkout was required.

**6 tests passed.** The suite combines controlled boundary tests and installed-application smoke tests. README describes the exact external-service boundary exercised. Model/agent/service outputs are fixtures, not live inference or real external actions. These checks establish application assembly and controls, not model quality, external account access, or production readiness.

The ZIP contains application source, fixtures, instructions and dependency metadata. It excludes installed third-party packages, virtual environments, credentials and model weights. This report was added after the clean run; the tested files remained unchanged.

```text
test_limits (test_reporting.ReportingTests.test_limits) ... ok
test_prohibited_operations (test_reporting.ReportingTests.test_prohibited_operations) ... ok
test_reference_result (test_reporting.ReportingTests.test_reference_result) ... ok
test_valid_sql_can_be_wrong (test_reporting.ReportingTests.test_valid_sql_can_be_wrong) ... ok
test_complete_report_both_sdks_and_failures (test_sdk.SDKTests.test_complete_report_both_sdks_and_failures) ... ok
test_private_data_and_units (test_sdk.SDKTests.test_private_data_and_units) ... ok

----------------------------------------------------------------------
Ran 6 tests in 11.859s

OK
```

---

Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved

Licensed under the [MIT License](LICENSE.txt). Provided without warranty; use at your own risk. See the [disclaimer](DISCLAIMER.md).
