# Editorial acceptance criteria

Judge each version against the original source packet and brief. The free service is assessment; parts cost extra and require prior approval. Repair success isn't guaranteed. Advance booking and the capacity limit must survive, as must both access conditions. The brief's style example supplies no workshop facts. Never invent a booking address.

Mechanical checks examine literal presence, numeric components, terminology, and whitespace word counts. They don't establish whether a statement is true, whether a qualification was omitted, or whether a translation says what its author intended. Review each `must_keep` statement in each output and record the supporting wording or defect. The variant needs a qualified reviewer of the selected language.

`review_cases.jsonl` contains deliberately constructed drafts and expected judgments. Use them to check whether the review procedure notices known defects. They are not generated live-model results. The Spanish defect requires qualified language review; do not treat an English-only evaluator's approval as certification.

The folders under `live/` each contain runnable sources and a brief. The expected results are in `expectations.json`. Run each packet through both methods using the same provider configuration. Keep generation cases separate from the deliberately altered review drafts. The impossible-budget case may yield an explicit question or a draft that mechanical checks hold; neither is approvable as-is.

For a blinded assessment, hide the method, fact plan, and call metadata initially. Supply each draft with the common original sources and brief. Record accepted/rejected, defect type, corrected wording, reviewer minutes, and any unresolved question. Reveal methods afterward and use `editorial compare` for generation metrics. A lower call count or an empty mechanical flag list isn't proof of useful output.

Retain the package fingerprint with each assessment. Corrections are new packages. Changing the audience, translation language, or document purpose needs fresh examples and qualified review for that use.
