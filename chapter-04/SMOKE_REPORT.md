# Chapter 4 application smoke report

Clean ZIP installation tested on October 3, 2026 with Python 3.12 on Linux. Extracted into a fresh directory and installed with `uv sync --locked --no-editable`. Every installed Python module matched the archived source. No earlier chapter checkout was required.

**22 tests passed.** The suite combines controlled boundary tests and installed-application smoke tests. README describes the exact external-service boundary exercised. Model/agent/service outputs are fixtures, not live inference or real external actions. These checks establish application assembly and controls, not model quality, external account access, or production readiness.

The ZIP contains application source, fixtures, instructions and dependency metadata. It excludes installed third-party packages, virtual environments, credentials and model weights. This report was added after the clean run; the tested files remained unchanged.

```text
test_01_extraction_guards (test_controls.ChapterChecks.test_01_extraction_guards) ... ok
test_02_empty_pdf_is_held (test_controls.ChapterChecks.test_02_empty_pdf_is_held) ... ok
test_03_chunk_identity_overlap_and_failures (test_controls.ChapterChecks.test_03_chunk_identity_overlap_and_failures) ... ok
test_04_embedding_prefixes_normalization_and_drift (test_controls.ChapterChecks.test_04_embedding_prefixes_normalization_and_drift) ... ok
test_05_retrieval_modes (test_controls.ChapterChecks.test_05_retrieval_modes) ... ok
test_06_member_model_inputs_exclude_restricted_data (test_controls.ChapterChecks.test_06_member_model_inputs_exclude_restricted_data) ... ok
test_07_organizer_answer_has_traceable_source (test_controls.ChapterChecks.test_07_organizer_answer_has_traceable_source) ... ok
test_08_revocation_during_retrieval_stops_first_model_stage (test_controls.ChapterChecks.test_08_revocation_during_retrieval_stops_first_model_stage) ... ok
test_09_revocation_during_reranking_stops_composition (test_controls.ChapterChecks.test_09_revocation_during_reranking_stops_composition) ... ok
test_10_revocation_or_edit_during_composition_withholds_result (test_controls.ChapterChecks.test_10_revocation_or_edit_during_composition_withholds_result) ... ok
test_11_updates_deletion_and_atomic_replacement (test_controls.ChapterChecks.test_11_updates_deletion_and_atomic_replacement) ... ok
test_12_version_changes_and_model_namespaces (test_controls.ChapterChecks.test_12_version_changes_and_model_namespaces) ... ok
test_13_invalid_answers_are_rejected (test_controls.ChapterChecks.test_13_invalid_answers_are_rejected) ... ok
test_14_traceability_does_not_prove_meaning (test_controls.ChapterChecks.test_14_traceability_does_not_prove_meaning) ... ok
test_15_clarification_conflict_and_absence_shapes (test_controls.ChapterChecks.test_15_clarification_conflict_and_absence_shapes) ... ok
test_16_reranking_rejects_unknown_duplicate_and_excess_ids (test_controls.ChapterChecks.test_16_reranking_rejects_unknown_duplicate_and_excess_ids) ... ok
test_17_context_budget_preserves_whole_passages (test_controls.ChapterChecks.test_17_context_budget_preserves_whole_passages) ... ok
test_18_matching_excludes_unknown_and_ineligible_venues (test_controls.ChapterChecks.test_18_matching_excludes_unknown_and_ineligible_venues) ... ok
test_19_matching_variation_integration (test_controls.ChapterChecks.test_19_matching_variation_integration) ... ok
test_20_evidence_coverage (test_controls.ChapterChecks.test_20_evidence_coverage) ... ok
test_22_request_bounds_and_no_access (test_controls.ChapterChecks.test_22_request_bounds_and_no_access) ... ok
test_complete_index_query_search_match_and_failure (test_sdk.SDKTests.test_complete_index_query_search_match_and_failure) ... ok

----------------------------------------------------------------------
Ran 22 tests in 6.481s

OK
```
