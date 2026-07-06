# Evaluation results

Dataset: **21 cases** (6 empty/precision), **18 labeled issues**. Model: gpt-5.4-mini (specialists) / gpt-5.4-mini (synthesizer). Matching: same file, line overlap within +/-3, each match manually confirmed as the same issue.

## Recall

- **In-scope recall: 14%** (2/14) — labels within the bot's three specialties (security / maintainability / test_coverage).
- **Overall recall: 11%** (2/18) — all labels, including 4 logic/correctness bugs (category=null) the bot has no agent for and cannot match by design.
- **Location-only recall (in-scope): 71%** (10/14) — the bot flagged the right code region, ignoring whether it identified the same issue. The gap from in-scope recall is how often it found the spot but not the problem.
- **In-scope must-fix recall: 33%** (1/3) — small sample, report as indicative.

### Per-category recall (in-scope)

- maintainability: 0% (0/5)
- security: 0% (0/2)
- test_coverage: 29% (2/7)

## Precision

- Bot emitted **56 findings** total across all cases.
- **2** were confirmed matches to a labeled issue.
- On the 6 empty cases, the bot emitted **11** finding(s) — guaranteed false positives (or real unlabeled issues; inspect each).

> Note: a finding that doesn't match a label isn't automatically a false positive — it may be a real issue the human reviewers didn't flag. Precision here is reported conservatively; unmatched findings warrant manual inspection rather than automatic FP labeling.

## Severity calibration (confirmed matches only)

- 1/2 confirmed matches had bot severity aligned with label importance (must_fix↔critical/high, nice_to_have↔medium/low).
  - django_django_21438: label=nice_to_have, bot severity=medium [ok]
  - home-assistant_core_88276: label=must_fix, bot severity=low [MISCALIBRATED]

## Cost & latency

- ~4 model calls/case (3 specialists + synthesizer); ~84 calls total.
- Total wall-clock: 120s; avg 5.7s/case.
- Run on gpt-5.4-mini.

## Headline finding

All in-scope catches are concentrated where added code sits on the flagged lines; the must-fix logic/correctness bugs (category=null) are missed wholesale — the bot localizes code regions but does not reason about correctness. This points to a dedicated logic/correctness agent as the clear next step.
