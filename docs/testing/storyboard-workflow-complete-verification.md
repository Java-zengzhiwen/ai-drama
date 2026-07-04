# Storyboard Workflow Complete Verification

Run the shared verification entrypoint from the repository root:

```bash
python3 tools/verify_storyboard_workflow.py
```

Optional overrides:

```bash
python3 tools/verify_storyboard_workflow.py \
  --repo-root . \
  --report-dir docs/testing/storyboard-workflow-verification
```

Default scratch paths:

- `/tmp/ai-drama-storyboard-complete-verification`
- `/tmp/ai-drama-storyboard-complete-verification-export`

Outputs:

- `storyboard-verification-report.md`
- `storyboard-verification-report.json`

Default report directory:

- `docs/testing/storyboard-workflow-verification`

The script always runs against temporary data roots and must not touch production runtime data.
