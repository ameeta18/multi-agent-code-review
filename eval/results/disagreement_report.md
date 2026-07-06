# Forward-adjudicated precision & disagreement analysis

Precision is scored forward from bot output, judged on merits independent of human labels — avoiding the incompleteness bias where a backward scorer counts real issues humans missed as false positives.

- **Actionable precision: 29%** (6/21) — how often the bot produces a finding worth surfacing (real defect or coverage gap that matters).
- **Factual precision: 86%** (18/21) — how often the bot is technically correct, regardless of whether the point is worth raising.
- **Gap (factual − actionable): 12** — technically-correct-but-not-worth-raising findings (the coverage agent's over-firing on trivial gaps).

## Severity of actionable findings

- critical 1, high 3, medium 2, low 0 (of 6).

## Three-bucket disagreement table

**A. Bot caught + human labeled same issue: 1** — recall hits.
**B. Bot raised + human silent/different: 20** — split:
   - **5 actionable (value-add humans didn't flag)**
   - 15 not actionable (trivia or false alarms)
**C. Human labeled + bot missed: 17** — recall misses (of 18, 1 caught).

## Headline: value beyond human review

Of findings the bot raised that humans did NOT confirm, **5 were actionable issues humans missed** — value a backward scorer structurally counts as false positives.

- **apache_airflow_59643** [security/high] Credential Exposure via Connection Test Endpoint
- **apache_airflow_6654** [test_coverage/critical] Potential ZeroDivisionError in exponential backoff calculation
- **encode_httpx_1349** [maintainability/medium] Duplicated IPv6 bracketing logic
- **encode_httpx_780** [test_coverage/high] Proxy initialization with partial credentials from URL
- **scikit-learn_scikit-learn_33787** [maintainability/medium] Duplicated callback handling for the final estimator

## Definitions & caveats

- Actionable = worth surfacing; Factual = technically correct. Both judged by the author against source (not an LLM, avoiding circularity). Single adjudicator. Coverage findings that are correct but low-severity count toward factual, not actionable precision. n=21, indicative.
