# M6D Management UI Verification

Date: 2026-07-13  
Branch: `feat/m6d-management-ui`  
Base: `feat/m6c-adapter-cutover@ef474f6a11badbf88833564b4909a8c8cf1b2505`

## Result

`READY_FOR_REVIEW`

M6D delivers local supplier management, supplier config and write-only credentials, immutable TypeScript adapter versions, stable model catalog management, project defaults and operation overrides, explicit CAS conflict recovery, loopback-only UX, and offline fake execution acceptance.

No real Provider request was made:

```text
REAL_TEXT_REQUEST_COUNT=0
REAL_IMAGE_REQUEST_COUNT=0
REAL_VIDEO_REQUEST_COUNT=0
```

## Acceptance evidence

| Criterion | Result | Evidence |
| --- | --- | --- |
| Supplier list/detail | PASS | Safe list projection, enable/disable, custom empty template, detail workbench |
| Config and independent ETag | PASS | Manifest-driven form, server-side typed-value merge, refreshed ETag on consecutive saves |
| Credential lifecycle | PASS | Write-only mutation, masked suffix, browser input clearing, active-job count, explicit force acknowledgement |
| TypeScript adapter editor | PASS | Lazy editor, local validation diagnostics, immutable save, built-in restore |
| Stable model management | PASS | UUID identity, overlay create/edit/disable/delete, binding acknowledgement, combined entity/catalog CAS |
| Project model routing | PASS | Capability-filtered defaults, operation overrides, inherited/explicit labels, resolution preview |
| Conflict handling | PASS | Browser acceptance for config, code, model, supplier, and binding stale revisions with reload action |
| Local-only management | PASS | Application guard regression plus stable `LOCAL_MANAGEMENT_ONLY` UX |
| Accessibility | PASS | Labels, dialog focus, tab/tabpanel associations, roving focus, arrow/Home/End navigation, destructive confirmations |
| Responsive design | PASS | Approved three-region desktop workbench; compact supplier selector at 768px |
| Fake execution | PASS | Browser-triggered V1 then V2 text execution; the same Playwright flow creates a queued video job and proves its snapshot hash and supplier version remain V1 after the V2 save |
| Zero real network | PASS | Browser rejects non-loopback requests; Worker test transport denies external DNS/TCP/UDP |

The active-credential force-delete behavior is the management operation frozen by the approved provider design: draft/queued jobs are cancelled and submitting/submitted/polling jobs fail locally with `credential_revoked`; no provider-side cancellation or resubmission is attempted. It does not alter normal M6C submission, polling, rerun, or snapshot routing behavior.

## Verification commands

```text
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q
598 passed, 1 skipped

npm --prefix web run test -- --run
93 passed, 3 skipped

npm --prefix web run build
PASS

npm --prefix web run test:e2e
8 passed

npm --prefix worker test
9 passed

python3 tools/verify_m3_agnes_generation.py
PASS

python3 tools/verify_m4_chapter_rehearsal.py
PASS

python3 tools/verify_m6b_model_catalog_binding.py
PASS

python3 tools/verify_m6c_adapter_cutover.py
PASS

python3 tools/verify_m6d_management_ui.py
M6D-001..M6D-015 PASS

python3 migration/tools/verify_migration.py
valid; checked_files=81

git diff --check
PASS
```

## Bundle and visual QA

The TypeScript editor remains a lazy chunk (`2.61 kB`, `1.30 kB` gzip). The M6D build produces a main JavaScript chunk of `1,029.51 kB` (`321.26 kB` gzip) and CSS of `13.41 kB` (`3.63 kB` gzip). Relative to the M6C baseline recorded during implementation (`965.10 kB`, `302.55 kB` gzip), main JavaScript increased by `64.41 kB` raw and `18.71 kB` gzip. No eager editor dependency was added.

Product Design QA is archived at `docs/product-design/m6d/design-qa.md`; the approved reference remains `docs/product-design/m6d/assets/selected-direction-supplier-operations-workbench.png`.

## Secret and evidence hygiene

- Supplier credentials are never returned by read APIs.
- Browser state does not write supplier data to localStorage or sessionStorage.
- Config URLs are projected without userinfo, query, or fragment.
- Three successful visual-QA screenshots are committed for 1440/1180/768 viewports. They use the built-in OpenAI model page and contain no credential form or secret value. Failure screenshots and first-retry traces remain temporary.
- Repository secret-pattern scan found no real API key, Bearer token, password, or signed URL. One pre-existing synthetic fixture string (`Bearer echoed-provider-token`) remains in a provider unit test.
- Sanitized evidence and zero-network tests passed; no real smoke test was run.

## Rollback

M6 supplier execution remains controlled by `M6_SUPPLIER_EXECUTION_ENABLED=false` by default. Disabling the flag retains the M6D management data and returns execution to the legacy M6C-off path without deleting supplier, model, binding, or historical job state.
