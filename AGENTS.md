## Phase 1 — Storyboard Canonicalization

Before any Phase 1 planning, implementation, testing, review, commit,
or push, read these files in full:

- `docs/superpowers/specs/2026-06-28-storyboard-canonical-shot-prompt-foundation-design.md`
- `docs/superpowers/specs/2026-06-29-phase-1-agent-execution-acceptance-contract.md`

Rules:

- Treat both documents as frozen and read-only.
- The Foundation Design defines the architecture.
- The Phase 1 contract defines execution, stop conditions, scope,
  verification, and completion.
- Do not modify either frozen document.
- Do not implement Phase 2 or later scope.
- The main agent is the only code-writing agent.
- Subagents are read-only unless the contract explicitly says otherwise.
- Stop and ask the user only when a contract Stop Condition is triggered.
- Do not weaken tests, schemas, fixtures, golden outputs, or acceptance checks.
- Do not declare completion without the unified Phase 1 verification PASS.
- Do not commit or push partial work after a Stop Condition.