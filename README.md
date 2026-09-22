# Jev Smart Retry

## Goal

Retry a failed CI command when [Jev](https://docs.typesafe.ai/introduction/quickstart) judges that running it unchanged could help. If the command passes, Jev is not called. If Jev declines or is unavailable, the Action keeps the command failure.

## Use

Add a TypeSafe AI key as the repository secret `TYPESAFE_API_KEY`, then wrap a safe command in the Action:

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

The command runs in Bash with `pipefail`; each retry starts a fresh shell but keeps any files or other effects from earlier attempts. Put setup and commands with side effects outside the retry step. The runner needs Bash and Python 3. Pin the Action to a commit SHA or release tag for production use.

## Configure

| Input | Default | Meaning |
| --- | --- | --- |
| `command` | required | Command to run |
| `typesafe-api-key` | required | Secret used only after failure |
| `max-retries` | `2` | Additional attempts, 0–5 |
| `retry-threshold` | `0.90` | Minimum Jev retry probability |
| `category-confidence` | `0.75` | Minimum category confidence |
| `retry-delay-seconds` | `2` | Seconds between attempts, 0–60 |

Jev must meet both thresholds and choose `network`, `runner`, `test_flake`, or `dependency` to trigger a retry. The Action sends the exit code and up to 12,000 characters of failed command output to Jev. Avoid commands that print secrets or private data; redaction is best effort.

Outputs: `attempts`, `recovered`, `category`, `retry-probability`, and `category-confidence`. The scores are between 0 and 1 and reflect the last valid Jev decision, including a decision to decline a retry. They are empty if Jev was not called or its call failed. The key and raw log are never outputs. See [calibration](docs/calibration.md) for an `if: always()` example and a simple evaluation record.

Run the unit tests with `python3 -m unittest discover -s tests -v`. A [manual live test](.github/workflows/jev-live-test.yml) ran once with a synthetic timeout; Jev declined the retry at the default threshold. That test does not establish accuracy on real CI failures.
