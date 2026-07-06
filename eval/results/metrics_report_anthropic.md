# Evaluation results

Dataset: **21 cases** (6 empty/precision), **18 labeled issues**. Model: claude-haiku-4-5 (specialists) / claude-haiku-4-5 (synthesizer). Matching: same file, line overlap within +/-3, each match manually confirmed as the same issue.

## Recall

- **In-scope recall: 14%** (2/14) — labels within the bot's three specialties (security / maintainability / test_coverage).
- **Overall recall: 11%** (2/18) — all labels, including 4 logic/correctness bugs (category=null) the bot has no agent for and cannot match by design.
- **Location-only recall (in-scope): 57%** (8/14) — the bot flagged the right code region, ignoring whether it identified the same issue. The gap from in-scope recall is how often it found the spot but not the problem.
- **In-scope must-fix recall: 0%** (0/3) — small sample, report as indicative.

### Per-category recall (in-scope)

- maintainability: 0% (0/5)
- security: 50% (1/2)
- test_coverage: 14% (1/7)

## Precision

- Bot emitted **68 findings** total across all cases.
- **2** were confirmed matches to a labeled issue.
- On the 6 empty cases, the bot emitted **15** finding(s) — guaranteed false positives (or real unlabeled issues; inspect each).

> Note: a finding that doesn't match a label isn't automatically a false positive — it may be a real issue the human reviewers didn't flag. Precision here is reported conservatively; unmatched findings warrant manual inspection rather than automatic FP labeling.

## Severity calibration (confirmed matches only)

- 1/2 confirmed matches had bot severity aligned with label importance (must_fix↔critical/high, nice_to_have↔medium/low).
  - apache_airflow_63530: label=nice_to_have, bot severity=critical [MISCALIBRATED]
  - django_django_21438: label=nice_to_have, bot severity=medium [ok]

## Cost & latency

- ~4 model calls/case (3 specialists + synthesizer); ~84 calls total.
- Total wall-clock: 234s; avg 11.1s/case.
- Run on claude-haiku-4-5.

## Headline finding

All in-scope catches are concentrated where added code sits on the flagged lines; the must-fix logic/correctness bugs (category=null) are missed wholesale — the bot localizes code regions but does not reason about correctness. This points to a dedicated logic/correctness agent as the clear next step.
