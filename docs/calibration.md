# Evaluate on real CI failures

Collect known transient failures and deterministic regressions before changing thresholds. For each failed command or test, record:

| Command/test | Redacted failure signature | Jev category | Retry probability | Category confidence | Retried? | Retry passed? | Human: retry appropriate? |
| --- | --- | --- | --- | --- | --- | --- | --- |

Link the CI run. If no retry occurred, record its outcome as unknown unless an independent rerun of the *unchanged* command established whether it would pass. Never record an API key or raw failure log.

The Action can fail after correctly declining a retry. Add this step after an Action step with `id: retry` to inspect its outputs:

```yaml
- name: Show Jev outputs
  if: always()
  env:
    RETRY_OUTPUTS: ${{ toJSON(steps.retry.outputs) }}
  run: printf '%s\n' "$RETRY_OUTPUTS"
```

Group results by category and retry probability range (`0–<0.25`, `0.25–<0.50`, `0.50–<0.75`, `0.75–<0.90`, `0.90–1.00`), plus `no decision`. Count failures, retries, and successful retries in each group. Track **incorrect retries** (human judged the retry inappropriate) and **missed recoveries** (a declined retry later passed unchanged) separately.

One synthetic timeout test is not evidence that Jev's probabilities are calibrated for CI. Review real examples from both groups before tuning the default thresholds.
