# M4 Rehearsal Runbook

## Purpose

M4 rehearsal is mock-provider only. It validates chapter production pipeline
traceability, failed-attempt retention, rerun behavior, local result
persistence, result selection, review records, and operator reporting.

It does not validate real Agnes network behavior or video quality.

## When to Run

Run after M4 or later changes that touch generation jobs, poller behavior,
result persistence, result selection, reviews, reruns, or report output.

## Command

```bash
python3 tools/verify_m4_chapter_rehearsal.py
```

## Expected Success Token

```text
M4_CHAPTER_REHEARSAL_PASS
```

## Report Paths

The verifier writes runtime artifacts outside git:

```text
runtime-data/reports/m4-chapter-rehearsal-report.json
runtime-data/reports/m4-chapter-rehearsal-report.md
```

## How to Read the Report

Use the Markdown report for operator review:

- `Executive Summary` confirms project, chapter, mock provider, and
  `real_agnes_request_made = false`.
- `Scenario Matrix` confirms `SHOT_001` source success and `SHOT_002` source
  failure followed by rerun success.
- `Shot Timeline` shows attempt number, job ID, status, and error code.
- `Result Version History` maps result IDs to source jobs, local content URLs,
  and object IDs.
- `Current Selection` shows the selected result for each shot.
- `Reviews` shows review ID and decision.
- `Operator Checklist` gives the human review checklist.
- `Deferred Items` lists work that remains outside the mock rehearsal.

Use the JSON report for automation. It includes `schema_version`,
`environment`, `scenarios`, `operator_checklist`, and `deferred_items` while
preserving the original M4 report fields.

## What Failure Means

A verifier failure means the local mock rehearsal no longer proves the chapter
production chain is traceable end to end. Read the failing assertion or report
section first, then check the smallest relevant layer: queue, poller, result
persistence, selection, review, rerun, or report rendering.

## Mock Rehearsal vs Real Agnes Smoke Test

M4 rehearsal uses a deterministic local mock backend. It makes no real HTTP
request to Agnes and does not require public HTTPS asset delivery.

Real Agnes smoke testing is separate. It requires provider configuration,
public HTTPS asset reachability, a configured Agnes API key, and explicit user
authorization.

## Deferred Real Provider Token

Real provider testing remains deferred until the user sends:

```text
AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST
```
