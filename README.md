# Jev Smart Retry

## Goal

Retry a failed CI command when [Jev](https://docs.typesafe.ai/introduction/quickstart) thinks it may pass if run again. If the command passes, the Action does not call Jev. If Jev declines or is unavailable, the command still fails.

## Use

Save your TypeSafe AI key as the repository secret `TYPESAFE_API_KEY`. Then wrap a safe command in the Action:

```yaml
steps:
  - uses: actions/checkout@v4
  - run: npm ci
  - uses: MakonnenMak/jev-smart-retry@main
    id: tests
    with:
      command: npm test
      typesafe-api-key: ${{ secrets.TYPESAFE_API_KEY }}
```

The command runs in Bash with `pipefail`. Each retry starts a fresh shell. Files and other changes from earlier attempts remain. Put setup and commands with side effects outside this step. The runner needs Bash and Python 3. For production, pin the Action to a commit SHA or release tag.

## Configure

| Input | Default | Meaning |
| --- | --- | --- |
| `command` | required | Command to run |
| `typesafe-api-key` | required | Secret used only after failure |
| `max-retries` | `2` | Additional attempts, 0–5 |
| `retry-threshold` | `0.90` | Minimum Jev retry probability |
| `category-confidence` | `0.75` | Minimum category confidence |
| `retry-delay-seconds` | `2` | Seconds between attempts, 0–60 |

To retry, Jev must meet both thresholds and choose `network`, `runner`, `test_flake`, or `dependency`. The thresholds are global defaults. Set them per workflow if needed. The Action does not set different thresholds for different categories. The Action sends the exit code and up to 12,000 characters of failed output to Jev. Avoid commands that print secrets or private data. Redaction is best effort.

The outputs are `attempts`, `recovered`, `category`, `retry-probability`, and `category-confidence`. The two scores are between 0 and 1. They show Jev's last valid decision, even when Jev declines a retry. They are empty when Jev was not called or the API call failed. The API key and raw log are never outputs.

## Evaluate

The Action can fail after Jev declines a retry. Add this step after the example to see the outputs:

```yaml
- name: Show Jev outputs
  if: always()
  env:
    RETRY_OUTPUTS: ${{ toJSON(steps.tests.outputs) }}
  run: printf '%s\n' "$RETRY_OUTPUTS"
```

Try it on real CI failures and compare Jev's decision with what happened. Keep the defaults until you have enough examples to decide whether your workflows need different values.

Run the unit tests with `python3 -m unittest discover -s tests -v`. A [manual live test](.github/workflows/jev-live-test.yml) ran with a synthetic timeout. Jev declined the retry at the default threshold. This does not show how well Jev works on real CI failures.
