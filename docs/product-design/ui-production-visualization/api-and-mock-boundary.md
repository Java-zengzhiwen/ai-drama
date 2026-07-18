# API and Mock Boundary

## Production API boundary

The frontend continues to consume the existing project/chapter, source/script, storyboard, profile/asset, requirement/prompt, generation/result/rerun, supplier/model/config/credential/code, and project-binding endpoints. No request payload, response shape, status value, credential behavior, idempotency rule, snapshot rule, or polling contract changed.

`web/vite.config.ts` now provides a development-only `/api` proxy to the existing loopback backend at `127.0.0.1:8000`. This enabled review of the current frontend without replacing the production backend or changing API semantics.

## Test and fixture boundary

- Unit tests mock only the existing Axios client.
- Playwright M1/M2 uses the local production application boundary.
- Existing M6D/M6E tests use their established loopback/fake-provider fixtures.
- No new runtime fixture, production seed, mock API route, or browser-only domain record was added.
- Manual screenshots use existing local project/chapter data.

## Network invariant

- `REAL_TEXT_REQUEST_COUNT=0`
- `REAL_IMAGE_REQUEST_COUNT=0`
- `REAL_VIDEO_REQUEST_COUNT=0`

The browser QA resource check found only local Vite resources and `/api/...` assets/results. No external Agnes, OpenAI, DeepSeek, xAI, Anthropic, or Aixora resource was requested.
