# Jev Smart Retry

Retry a failed CI command only when [Jev](https://docs.typesafe.ai/introduction/quickstart) finds strong evidence that rerunning it unchanged can help. A successful command never calls Jev. If Jev is unavailable, uncertain, or finds a likely code or configuration error, the action leaves the original failure intact.

## Use it

1. Add a TypeSafe AI key as the repository secret `TYPESAFE_API_KEY`.
2. Put the command you want to retry inside the action step:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - run: npm ci
      - uses: MakonnenMak/jev-smart-retry@main
        id: tests
        with:
          command: npm test
          typesafe-api-key: ${{ secrets.TYPESAFE_API_KEY }}
          max-retries: '2'
```

For production, pin `uses:` to a commit SHA or release tag once one exists. This action needs `bash` and `python3` on the runner; it works on GitHub hosted Ubuntu runners. Its command runs in a fresh Bash process on each attempt, with `pipefail` enabled, in the current working directory. Changes left by a failed attempt are **not** rolled back. Keep `npm ci`, build setup, and any non-idempotent operations outside the retried command. It does not rerun previous workflow steps or a whole job.

### Inputs

| Input | Default | Purpose |
| --- | --- | --- |
| `command` | required | Shell command to run |
| `typesafe-api-key` | required | TypeSafe AI key; used after failure |
| `max-retries` | `2` | Additional attempts, 0–5 |
| `retry-threshold` | `0.90` | Minimum probability the failure is retryable |
| `category-confidence` | `0.75` | Minimum confidence in a retryable failure category |
| `retry-delay-seconds` | `2` | Pause between attempts, 0–60 seconds |

Outputs: `attempts` (total command runs), `recovered` (`true` only if a retry succeeds), `category` (last valid failure category), `retry-probability` (Jev's Noul value, 0–1), and `category-confidence` (Jev's confidence in that category, 0–1). The two scores come from the last valid Jev decision, even when the action declines a retry and fails. They are empty if the command passes before Jev is called or the Jev API call fails. No API key or raw failure log is written to these outputs. Supported retry categories are `network`, `runner`, `test_flake`, and `dependency`. See [the calibration guide](docs/calibration.md) for collecting these outputs from real CI failures.

## How it decides

On failure, the action sends the exit code and the last 12,000 characters of command output to TypeSafe AI's Jev API. It asks two independent questions in one request: a yes/no `Noul` probability that the unchanged command will pass on retry, and a `Choice` failure category. It retries only when **both** the probability and category confidence exceed their thresholds and the category is retryable. Noul does not have a separate `confidence` field; its value is the yes probability. A high score is a heuristic, not proof that a test is flaky. The defaults have not yet been calibrated against real CI failures. [API documentation](https://docs.typesafe.ai/introduction/quickstart).

The original exit code is preserved for ordinary command failures, including API errors. Once the retry budget is exhausted, the final attempt's exit code is returned. Commands that expose credentials or private data in their output should not be used with this action: the output tail is transmitted to TypeSafe AI after a failure. The action attempts to redact environment variables with names containing `TOKEN`, `SECRET`, `PASSWORD`, or `API_KEY`, but this is best effort and does not cover every secret.

No TypeSafe API key is required to run the local unit tests:

```bash
python3 -m unittest discover -s tests -v
```

A [manual live Jev workflow](.github/workflows/jev-live-test.yml) has run once with a synthetic timeout. Jev selected `network` with retry probability `0.71` and category confidence `1.00`, and correctly declined the retry at the default `0.90` threshold. This single synthetic result does not establish calibration for real CI failures. Before relying on retry decisions, evaluate known transient failures and deterministic regressions using [the calibration guide](docs/calibration.md).
