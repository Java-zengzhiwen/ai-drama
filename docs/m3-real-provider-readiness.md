# M3 Real Provider Readiness

This guide prepares a real Agnes video smoke test. It must not be used to send
real Agnes video generation requests until the operator explicitly authorizes:

```text
AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST
```

## 1. Start App With Agnes Provider Env

Set runtime configuration outside git-tracked files:

```bash
AI_DRAMA_RUNTIME_PROVIDER=agnes
AI_DRAMA_PUBLIC_BASE_URL=https://<provider-reachable-domain>
AI_DRAMA_AGNES_VIDEO_RPM=1
AI_DRAMA_AGNES_POLL_INTERVAL_SECONDS=5
```

`AI_DRAMA_PUBLIC_BASE_URL` must be public HTTPS and provider-reachable. It must
not be `localhost`, `127.0.0.1`, private IP, link-local IP, `file://`, or a URL
with username/password.

## 2. Configure Agnes API Key

Do not write the real Agnes API key into `.env`, shell scripts, README files,
logs, or git-tracked files. Use the existing settings API or `LocalSecretStore`.

Settings API example with a placeholder only:

```bash
curl -X PUT http://127.0.0.1:8000/api/settings/agnes \
  -H 'Content-Type: application/json' \
  -d '{"api_key":"<AGNES_API_KEY>"}'
```

The API stores the key in `LocalSecretStore` and returns only configured status
plus a masked suffix.

## 3. Verify Masked Key Status

```bash
curl http://127.0.0.1:8000/api/settings/agnes
```

Expected shape:

```json
{"configured":true,"masked_suffix":"1234"}
```

The full key must never be returned to the browser.

## 4. Verify Public Asset URL Dry Run

Before any real provider request, verify locally:

- usable image asset can produce a signed public asset URL;
- URL scheme is HTTPS and host is provider-reachable;
- signature validates locally;
- expired signature is rejected;
- altered asset id is rejected;
- non-image assets are rejected.

This dry run must not call the Agnes video generation endpoint.

## 5. Confirm No Real Agnes Request Has Been Made

Allowed before authorization:

- local app startup;
- local verifier;
- local signed URL validation;
- configuration report.

Forbidden before authorization:

- `POST https://apihub.agnes-ai.com/v1/videos`;
- any real Agnes video generation request.

## 6. Request Authorization

After env, public URL, API key, and dry-run checks are ready, ask for:

```text
AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST
```
