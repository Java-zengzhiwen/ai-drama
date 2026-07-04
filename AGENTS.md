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

---

## Phase 3 — Shot Prompt Canonical Foundation

Before any Phase 3 planning, implementation, testing, review, commit,
or push, read these files in full:

- `docs/superpowers/specs/2026-07-01-phase3-shot-prompt-canonical-design.md`
- `docs/superpowers/specs/2026-07-04-phase-3-agent-execution-acceptance-contract.md`
- `docs/superpowers/plans/2026-07-03-phase3-shot-prompt-canonical-program.md`
- the current approved subphase plan for Phase 3A, 3B, 3C, 3D, or 3E

Rules:

- Treat the Phase 3 Design and Phase 3 Agent Execution Contract as frozen and read-only.
- The Phase 3 Design defines architecture and behavior.
- The Phase 3 Agent Execution Contract defines roles, permissions, stop conditions,
  scope, verification, and completion.
- Phase 3 is executed in strict order:
  `3A Store/Migration -> 3B Canonical/Validators -> 3C Renderer/Bundle
  -> 3D Review/Approval/Service/CLI -> 3E Skill/Verifier`.
- Do not enter a later subphase until the current subphase passes its acceptance gate.
- Do not enter Phase 4.
- Use subagent-driven development.
- The controller agent coordinates the work and does not write business code.
- Writable implementer subagents may modify only the current cluster allowlist.
- Read-only preflight, spec review, code quality review, and final integration
  subagents must not modify files, commit, or push.
- Only one writable implementer may operate in the implementation worktree at a time.
- Read-only preflight agents may run in parallel.
- Writable implementation clusters run sequentially.
- Reviewers return findings to the same implementer for repair.
- Do not ask the user to approve non-design execution fixes.
- Stop and ask the user only when a Phase 3 Stop Condition is triggered.
- Do not weaken tests, schemas, fixtures, golden outputs, migration guarantees,
  or acceptance checks.
- Do not push.
- Do not declare a subphase complete without its cluster reviews, focused tests,
  regressions, full verification, changed-file scope check, and clean worktree.
- Do not declare Phase 3 complete without the Phase 3E final verifier PASS.
