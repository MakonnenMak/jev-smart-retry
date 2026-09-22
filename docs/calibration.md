# Evaluating Jev on real CI failures

Collect examples from your own CI before changing retry policy. Include known transient failures (such as a registry timeout) and deterministic regressions (such as a reproducible assertion or compile error). Use a bounded, safe command: each retry runs the same command again and does not undo effects of earlier attempts. Redact credentials and private data from the failure signature; command output can be sent to Jev after a failure.

Record one row per failed command or test. Keep the human assessment independent of Jev's decision, and mark uncertain cases for review.

| Command or test | Brief redacted failure signature | Jev category | Retry probability | Category confidence | Retried? | Retry passed? | Human assessment: was retry appropriate? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Example: package install | Registry request timed out; URL redacted | network | 0.96 | 0.91 | Yes | Yes | Yes: known temporary outage |
| Example: unit test | Expected 3, got 4 | code_regression | 0.12 | 0.95 | No | N/A | No: reproducible assertion |

The example rows illustrate the format; they are not measurements. For each real row, link the CI run and note whether the failure reproduced on an independent rerun or was fixed by a code/configuration change. An unattempted retry has an unknown outcome; do not mark it as a missed recovery solely because its signature looks transient.

The action can correctly fail after declining a retry. Inspect its outputs in a later step using `if: always()`:

```yaml
- uses: MakonnenMak/jev-smart-retry@main
  id: retry
  with:
    command: npm test
    typesafe-api-key: ${{ secrets.TYPESAFE_API_KEY }}
- name: Record Jev decision
  if: always()
  env:
    CATEGORY: ${{ steps.retry.outputs.category }}
    RETRY_PROBABILITY: ${{ steps.retry.outputs.retry-probability }}
    CATEGORY_CONFIDENCE: ${{ steps.retry.outputs.category-confidence }}
    ATTEMPTS: ${{ steps.retry.outputs.attempts }}
    RECOVERED: ${{ steps.retry.outputs.recovered }}
  run: |
    printf 'category=%s retry-probability=%s category-confidence=%s attempts=%s recovered=%s\n' \
      "$CATEGORY" "$RETRY_PROBABILITY" "$CATEGORY_CONFIDENCE" "$ATTEMPTS" "$RECOVERED"
```

Empty scores mean there was no usable Jev decision for that run. Keep the API key and raw failure log out of recorded outputs.

Summarize counts by Jev category and retry probability range (`0–<0.25`, `0.25–<0.50`, `0.50–<0.75`, `0.75–<0.90`, `0.90–1.00`), with a separate `no decision` group. For each group, count total failures, retries, successful retries, human-approved retries, and human-rejected retries. Track **incorrect retries** (a retry made despite a human assessment that it was inappropriate) separately from **missed recoveries** (a declined retry later shown by an independent unchanged rerun to have succeeded). Note the evidence for each disputed case.

The one synthetic live workflow run classified a timeout as `network` but assigned retry probability `0.71`, so it declined at the default `0.90` threshold. It is not evidence that Jev's probabilities are calibrated for CI. Review real examples, including both transient failures and deterministic regressions, before tuning the default thresholds.
