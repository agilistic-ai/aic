# Chapter 9 application smoke report

Clean ZIP installation tested on October 3, 2026 with Python 3.12 on Linux. Extracted into a fresh directory and installed with `uv sync --locked --no-editable`. Every installed Python module matched the archived source. No earlier chapter checkout was required.

**11 tests passed; 0 skipped.** The suite combines controlled boundary tests and installed-application smoke tests. README describes the exact external-service boundary exercised. Model/agent/service outputs are fixtures, not live inference or real external actions. These checks establish application assembly and controls, not model quality, external account access, or production readiness.

The ZIP contains application source, fixtures, instructions and dependency metadata. It excludes installed third-party packages, virtual environments, credentials and model weights. This report was added after the clean run; the tested files remained unchanged.

```text
test_01_manifest_integrity (test_controls.Checks.test_01_manifest_integrity) ... ok
test_02_consent_and_invalid_audio_cleanup (test_controls.Checks.test_02_consent_and_invalid_audio_cleanup) ... ok
test_03_changed_media (test_controls.Checks.test_03_changed_media) ... ok
test_04_visual_provenance (test_controls.Checks.test_04_visual_provenance) ... ok
test_05_voice_quotes (test_controls.Checks.test_05_voice_quotes) ... ok
test_06_conflict_and_uncertainty (test_controls.Checks.test_06_conflict_and_uncertainty) ... ok
test_07_review_and_stale_draft (test_controls.Checks.test_07_review_and_stale_draft) ... ok
test_08_joint_preserves_provenance (test_controls.Checks.test_08_joint_preserves_provenance) ... ok
test_09_staged_pipeline_and_failed_stage (test_controls.Checks.test_09_staged_pipeline_and_failed_stage) ... ok
test_10_speech_keeps_text_path_independent (test_controls.Checks.test_10_speech_keeps_text_path_independent) ... ok
test_complete_staged_joint_pdf_review_and_speech (test_sdk.SdkTests.test_complete_staged_joint_pdf_review_and_speech) ... ok

----------------------------------------------------------------------
Ran 11 tests in 15.485s

OK
```
