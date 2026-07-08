# M3 Baseline Summary

## Merged Commit

M3 was merged to `main` by fast-forward at:

```text
f6d17d570b0b1906e02bbe7496446b91df604a26
fix: align agnes duration timing and input errors
```

After the readiness documentation update, `main` advanced to:

```text
265e31dfdb9e5dad7b797eef3c64bedf1e761b59
docs: add m3 real provider readiness guide
```

## Scope Completed

M3 completed the mock/TDD/verifier path for Agnes generation:

- persistent generation jobs and results;
- signed temporary asset delivery;
- explicit Agnes video status/result provider paths;
- queued submission, poller refresh, restart recovery, and terminal states;
- local video result byte persistence and result content endpoint;
- idempotent submit and controlled rerun schema;
- result selection, review, version history, and rerun UI;
- M3 verifier coverage.

M3 code path is complete for mock/TDD/verifier.

## Verification Summary

The merged M3 baseline passed:

- full Python test suite;
- M1 verifier;
- M2 asset and shot prompt verifiers;
- M3 Agnes generation verifier;
- migration verifier;
- Web unit tests;
- Web build;
- Web end-to-end tests;
- diff whitespace check;
- provider ID heuristic scan.

## Real Provider Smoke Test

Real Agnes smoke test is deferred.

Reason:

```text
M3_REAL_PROVIDER_NOT_READY
```

Missing runtime environment:

- `AI_DRAMA_RUNTIME_PROVIDER=agnes`;
- provider-reachable HTTPS `AI_DRAMA_PUBLIC_BASE_URL`;
- Agnes API key configured in `LocalSecretStore`.

Real Agnes smoke test is blocked by runtime environment, not implementation.

No Agnes generation request was made.

## Environment Requirements

Before a real Agnes smoke test:

```bash
AI_DRAMA_RUNTIME_PROVIDER=agnes
AI_DRAMA_PUBLIC_BASE_URL=https://<provider-reachable-domain>
AI_DRAMA_AGNES_VIDEO_RPM=1
AI_DRAMA_AGNES_POLL_INTERVAL_SECONDS=5
```

The Agnes API key must be configured through `LocalSecretStore` or the existing
`/api/settings/agnes` endpoint. Do not store the key in git-tracked files.

`AI_DRAMA_PUBLIC_BASE_URL` must be HTTPS and publicly reachable by Agnes. It
must not be localhost, loopback, private IP, link-local IP, `file://`, or a URL
with username/password.

## Deferred Item

Real smoke test remains opt-in only. The required authorization token is:

```text
AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST
```
