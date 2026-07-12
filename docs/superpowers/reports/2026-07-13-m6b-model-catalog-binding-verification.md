# M6B Model Catalog And Binding Verification

## Result

- Stage: M6B Model Catalog And Binding
- Result: READY_FOR_REVIEW
- Branch: `feat/m6b-model-catalog-binding`
- Approved base: `8187bd374e7e03d1e8ffafd68ed15cc4f53aecb3`
- Reviewed implementation head: `a96fbd52fd9a4ff1fd63cb9c410caa2181b8a4bd`
- Implementation started: true
- Real text requests: 0
- Real image requests: 0
- Real video requests: 0

M6B adds stable supplier model identities, immutable model revisions, manifest base
model synchronization, independent catalog revisions, project defaults and
operation overrides, fail-closed resolution, immutable provider-neutral execution
snapshots, snapshot-aware idempotency contracts, and loopback-only management
APIs. It does not cut over production adapters or the poller and does not add UI.

## Verification

All commands ran without real Provider authorization. Default Python and Node
test transports denied unexpected real network access.

| Check | Result |
| --- | --- |
| `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q` | PASS: 564 passed, 1 skipped |
| `npm --prefix web run test -- --run` | PASS: 60 passed, 2 skipped |
| `npm --prefix web run build` | PASS |
| `npm --prefix web run test:e2e` | PASS: 2 passed |
| `npm --prefix worker test` | PASS: 3 passed |
| `python3 tools/verify_m3_agnes_generation.py` | PASS |
| `python3 tools/verify_m4_chapter_rehearsal.py` | PASS |
| `python3 tools/verify_m6b_model_catalog_binding.py` | PASS: 13 checks, real request counts all zero |
| `python3 migration/tools/verify_migration.py` | PASS: 81 files checked |
| `git diff --check` | PASS |

The M6B verifier creates only temporary fake supplier/model/project data. It
exercises manifest migration, stable base/overlay isolation, immutable revisions,
catalog and binding revisions, fail-closed resolution, snapshot persistence,
idempotency conflicts, loopback enforcement, migration replay, legacy schema
preservation, and validation-mode network rejection through the isolated Worker.

## Acceptance Evidence

- Manifest declarations with explicit UUIDs retain the same stable model identity
  across code saves; legacy declarations receive deterministic supplier-scoped
  UUIDv5 identities during migration.
- Manifest base models and overlay models are unioned by stable identity. Removed
  base declarations are disabled rather than silently replaced or deleted.
- Built-in restore validates the selected immutable manifest and synchronizes the
  catalog in the same `BEGIN IMMEDIATE` transaction as the supplier pointer CAS.
- Active duplicate `(supplier, capability, provider_model_name)` checks run inside
  catalog write transactions.
- Project defaults use nullable model foreign keys; operation overrides use model
  foreign keys; complete binding sets update through one revision CAS.
- Resolver order is operation override, then capability default, then
  `MODEL_BINDING_MISSING`; supplier/model disable and capability mismatch fail
  closed without Worker or network calls.
- Snapshot persistence validates supplier/version/model/config ownership,
  immutable object hashes, model/provider identity, credential ownership/state,
  rate bucket, compiler/runtime/helper fingerprints, and snapshot index fields.
- Missing or incompatible immutable artifacts/runtime return
  `SUPPLIER_RUNTIME_UNAVAILABLE`.
- New idempotency records are scoped by supplier, capability, and key, and include
  the canonical request plus snapshot hash. Legacy generation uniqueness remains
  `UNIQUE(provider, idempotency_key)`.

## Review Record

Two independent read-only reviewers examined the implementation. Both performed
focused verification and made no file modifications or real Provider requests.

### Specification Compliance

Initial result: `REQUEST_CHANGES`.

Findings covered missing manifest catalog migration/sync, default binding foreign
keys, concurrent duplicate-name enforcement, project-binding acknowledgement
semantics, manifest rate bucket persistence, runtime compatibility validation,
and verifier checks that did not yet exercise the claimed behavior.

Corrections were implemented with red tests in commit `012b519`. Final result on
the corrected branch: `SPEC_REVIEW=PASS`, `BLOCKERS=NONE`.

### Technical And Security

Initial result: `REQUEST_CHANGES`.

Findings covered default binding FK/TOCTOU behavior, snapshot field/object and
credential forgery, manifest upgrade backfill, rate bucket provenance, and later
the built-in restore/catalog synchronization transaction.

The primary corrections landed in `012b519`; restore synchronization and its
rollback regression landed in `a96fbd5`. Final result:
`TECHNICAL_SECURITY_REVIEW=PASS`, `BLOCKERS=NONE`.

## Safety Scan

- No production Provider adapter, generation poller, generation execution route,
  or Web UI file changed from the M6A base.
- Added URL hits are `.invalid` test endpoints only.
- Sensitive-term hits are ETag variable names and explicit negative assertions;
  no credential value, bearer value, signed URL, or Provider response is present.
- No `runtime-data`, SQLite database, generated private result, or secret file is
  tracked.
- Real request counters remained text=0, image=0, video=0.

## Rollback

1. Stop M6B model/binding/snapshot writes and deploy the approved M6A commit.
2. Remove or disable registration of M6B model and project-binding routes; M6A
   supplier routes remain available.
3. Preserve M6B rows for audit, or restore the pre-M6B schema backup if physical
   rollback is required. M6B migrations are additive and do not rewrite M1-M5
   generation history.
4. Do not delete immutable supplier/model/snapshot objects while any M6B row
   references them.
5. Restart on M6A. Production provider selection, adapters, poller, generation
   jobs, and legacy idempotency continue unchanged because M6C cutover has not
   started.

## Known Warnings

- Snapshot validation currently invokes `node --version`; M6C may cache the
  sanitized runtime fingerprint per process without changing snapshot semantics.
- Model PATCH/DELETE uses a combined model/catalog `If-Match` token list and
  returns catalog state in `X-Model-Catalog-ETag`; M6D must preserve this client
  contract unless a separately reviewed API revision changes it.
- Content-addressed objects written before a losing SQL CAS may remain
  unreferenced. They are identifiable for later M6E garbage collection.
- Existing Starlette/httpx and asyncio policy deprecation warnings remain.
- The Web build retains the existing large-chunk warning.
