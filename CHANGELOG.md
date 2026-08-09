# Changes after the hackathon submission

The work was built at the Global South AI Safety Hackathon in June 2026. Going
back over it afterwards turned up several things worth correcting. They are
listed here so that anyone comparing this repository against the submitted
report can see what moved and why.

Nothing here changes the headline result. Two of the corrections make it
stronger, and one lowers a claim we had made.

## Statistics

**The locale gap is not statistically significant, and we have gone back to
saying so.** The design is paired: the same prompt is run for each locale, and
only the locale token changes. McNemar's test on matched pairs is the correct
test, and it gives p = 0.08 for the pooled African-versus-Western gap. The
submitted report reported this correctly. A later write-up used a
two-proportion z-test instead and reported p < 0.01; that test ignores the
pairing and overstates the result. The matched-pairs analysis stands.

This makes the central finding cleaner rather than weaker: there is no reliable
locale gap, because the guardrails are absent everywhere.

**Confidence intervals and a power analysis have been added.** The submitted
report gave per-arm Wilson intervals but no interval on any difference and no
power calculation. `src/analysis.py` now reports both. Detecting a one-point
locale gap against a ceiling near 98% would need on the order of 4,000
malicious prompts per region, against the 200 per arm used here, which is why
the locale comparison is underpowered by construction.

**Unparsed judgements are not missing at random.** Roughly 1-3% of responses
could not be parsed by the judge and were dropped. All eighteen were read by
hand. Under the base condition every one is a compliance; under the
constitution every one is a refusal. Excluding them therefore understates the
base rate and overstates the constitution rate. `src/analysis.py` reports the
result both ways so the bracket is visible. Correcting for it strengthens both
findings.

## Data and code

**The Pennsylvania prompt file in this repository had `stage` and `use_case`
swapped** relative to the other three arms, and used a different `subject_id`
scheme. It has been replaced with the aligned version. The reported numbers are
unaffected: the summary buckets on the `arm` and `is_false` columns and never
reads `stage` or `use_case`.

**The UK arm was missing from this repository** and has been added, so the
repository now contains all four arms described in the report.

**The judge configuration in the committed evaluation script named
`mistral-7b-instruct-v0.3`**, which is one of the models on the excluded
small-model list. That was a leftover smoke-test setting. The judging script
that produced the reported labels uses `llama-3.1-8b-instruct`, and both
scripts are now published.

**Compliance labels for the Kenya and South Africa arms are now included**, so
the reported African numbers can be recomputed from source.

## Prompts

**Instantiated false claims have been replaced with placeholders**, which is
what the report and preprint said was released. See `docs/DISCLOSURE.md`. The
files were public in unredacted form between June and August 2026, so this
limits further distribution rather than undoing the original release.

**Official names are now placeholders.** The prompt files previously asserted
that all named officials were synthetic. One name in the South Africa arm
matched a real member of parliament, so that assertion was not true as
published.

## Open items

**The two temperatures in the write-ups are two runs, not a contradiction.** The
audit was first run at temperature 1 with top_p 0.95 and top_k 40, matching
DisElect, which is what the submitted report describes. It was then re-run at
temperature 0 and the compliance pattern held. The evaluation script in this
repository sets 0. Both write-ups were therefore describing a real run, but
neither said that two were done, which made them look inconsistent. The stable
result across decoding settings is worth reporting as a robustness check rather
than buried as a parameter note.

**Two arms cite Wikipedia as a corroborating source** alongside the electoral
commission. The primary sources are official; the corroborating links should be
tightened.

**The Pennsylvania arm is anchored to the 2026 election**, which had not yet
taken place when the responses were generated in June 2026, while the other
three arms use completed elections. Models hedge about future events, and those
hedges are scored as non-compliance. Pennsylvania is a Western arm, and Western
is the side with lower compliance, so this is a plausible alternative
explanation for part of the small locale difference.
