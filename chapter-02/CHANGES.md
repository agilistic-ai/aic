# Assembly changes from the original Chapter 2 manuscript

The download includes Chapter 1's actual provider adapter and input/configuration helpers, plus locked dependencies and both provider configurations. The manuscript's instruction to retrofit an output-token argument was outdated after the Chapter 1 app work; the current adapter already supports it. Selected settings now pass explicitly through batch processing to extraction.

A duplicate warning previously disappeared when review recomputed validation problems. Approval now requires a separate duplicate acknowledgement, recorded in the audit result. The existing date acknowledgement still cannot clear other validation failures.

The recipe snapshot previously read code from the current working directory and always read `config.toml`. It now records the running package, selected configuration and effective endpoint, validated reference registry, lockfile, Python version, and installed direct dependency versions. This works after a normal package installation and when invoked from another directory with an explicit project path.

Input reads are bounded before import. Oversized files receive a visible `not_imported` result, and later inputs continue. The immutable arrival record and pending case are inserted together. Attempt completion uses a version check so a stale write cannot replace a newer case result. Reruns print skipped records with their existing state and recipe, making checkpoints visible.

The new CLI covers queue inspection, version-bound editable review files, decisions, and ready-record export for a specified recipe. Exports retain the complete source. Unknown files/cases and invalid review input produce concise errors. The original module-style batch entry point is retained.

The revised chapter preserves all five original main sections and aligns its printed modules and commands with the download. Shared adapter code and the CLI/snapshot support modules are in the download rather than repeated in full in the chapter. The static AIC outline document is unchanged.
