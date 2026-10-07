# Chapter 1 application smoke report

Status: PASS — nine smoke tests, including multiple provider and stream combinations.

The source archive was extracted into a fresh directory. `uv sync --locked --no-editable` created a new virtual environment and installed the application as a built package. The installed package then ran `python -m unittest discover -s tests -v`. Test commands also ran from temporary working directories with explicit configuration and input paths, avoiding an accidental dependency on the source working directory.

Reference environment: Linux, Python 3.12.14. Direct dependencies: OpenAI 2.54.0, Ollama 0.6.3, Pydantic 2.13.5, HTTPX 0.28.1 with SOCKS support. uv.lock records the complete dependency resolution.

The real OpenAI and Ollama SDKs were installed and used. Neither SDK nor the application's conversion function was replaced by a stub. The remote model services were represented by a temporary loopback HTTP server returning predetermined protocol responses. These tests make no live provider calls, use no actual credentials, and perform no inference.

The smoke suite exercised the installed console command and Python module CLI, along with the reusable Python function. Both provider branches accepted complete ordinary and streamed results. The tests rejected malformed output, extra fields, invalid calendar dates, dates absent from the source, invalid UTF-8, and oversized or empty notes. Refusals, interrupted streams, timeouts, and service failures emitted no task JSON. The timeout and service-error cases each made one request. A missing key produced a configuration error; help remained usable without one. Evaluation output preserved its pending semantic-review status and refused accidental overwrite.

The initial dependency installation exposed a missing SOCKS transport extra; the released dependency set fixes that import failure. All nine checks passed on the initial application run and again from the clean extracted source. Only this report was added after the extracted-source run; every source, test, configuration, and dependency file in the final archive was byte-compared with the tested extraction.

Not exercised: live hosted inference, a real Ollama server/model, model interpretation quality, account-specific model availability, and macOS/Windows installation. The live evaluation command and cases are supplied for those model checks. The local HTTP fixture result is not a model-quality benchmark.

## Recorded output

```text
test_01_cli_both_sdks_and_stream_modes (test_smoke.SmokeTests.test_01_cli_both_sdks_and_stream_modes) ... ok
test_02_reusable_function (test_smoke.SmokeTests.test_02_reusable_function) ... ok
test_03_validation_rejects_provider_output (test_smoke.SmokeTests.test_03_validation_rejects_provider_output) ... ok
test_04_failure_and_partial_stream_never_print_task (test_smoke.SmokeTests.test_04_failure_and_partial_stream_never_print_task) ... ok
test_05_bad_input_before_model_call (test_smoke.SmokeTests.test_05_bad_input_before_model_call) ... ok
test_06_configuration_and_help_need_no_model (test_smoke.SmokeTests.test_06_configuration_and_help_need_no_model) ... ok
test_07_network_failures_are_bounded_and_not_retried (test_smoke.SmokeTests.test_07_network_failures_are_bounded_and_not_retried) ... ok
test_08_missing_deadline_stays_null (test_smoke.SmokeTests.test_08_missing_deadline_stays_null) ... ok
test_09_evaluation_runner_preserves_review_requirement (test_smoke.SmokeTests.test_09_evaluation_runner_preserves_review_requirement) ... ok

----------------------------------------------------------------------
Ran 9 tests in 21.829s

OK
```
