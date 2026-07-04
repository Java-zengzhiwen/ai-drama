# Phase 3 Agent Execution Acceptance Contract

Date: 2026-07-04
Status: DRAFT_FOR_USER_REVIEW

## 1. Purpose

This contract governs agent roles and execution behavior for the complete
Phase 3 Shot Prompt Canonical Foundation program.

It reduces human handoffs while preserving strict scope, design, migration,
test, and review controls.

The frozen Phase 3 Design remains the architectural authority. This contract
does not change the design.

## 2. Program Order

Phase 3 runs in strict sequence:

1. Phase 3A — Store and Migration
2. Phase 3B — Canonical and Validators
3. Phase 3C — Renderer, Candidate Outputs, Bundle, and Integrity
4. Phase 3D — Review, Qualification, Approval, Service, and CLI
5. Phase 3E — Skill Package, Verifier, and Final Phase 3 Acceptance

A later subphase may not begin before the current subphase passes its acceptance
gate.

Phase 4 is not authorized by this contract.

## 3. Agent Roles

### 3.1 Main Controller

The controller:

- reads the frozen design, program index, current subphase plan, and repository state;
- creates the implementation worktree and branch;
- dispatches preflight, implementer, spec review, quality review, and final review agents;
- curates exact context for every subagent;
- tracks cluster status and commits;
- resolves non-design execution defects;
- enforces allowlists and stop conditions;
- writes no business implementation code.

The controller may update the current subphase plan only to correct execution
details that do not alter the frozen design.

### 3.2 Writable Implementer

A writable implementer:

- receives one cluster at a time;
- may modify only the cluster allowlist;
- follows TDD for production work;
- runs focused tests and cluster regressions;
- commits the cluster changes;
- self-reviews before returning;
- repairs findings returned by read-only reviewers.

Only one writable implementer may use the implementation worktree at a time.

### 3.3 Read-only Preflight Agents

Preflight agents may run in parallel.

They inspect:

- task-local executability;
- repository signatures;
- symbol and import paths;
- file ownership;
- old-test compatibility;
- schema and migration contracts;
- transaction ownership;
- SQLite foreign-key behavior;
- acceptance commands;
- current-plan scope.

They must not modify files, commit, or push.

The controller aggregates all preflight findings before implementation starts.

### 3.4 Read-only Spec Reviewer

The spec reviewer verifies:

- compliance with the frozen design;
- compliance with the current cluster contract;
- no missing required behavior;
- no extra Phase 3 or Phase 4 behavior;
- no protected-file changes;
- no weakened tests or contracts.

The spec reviewer must not modify files.

### 3.5 Read-only Code Quality Reviewer

The quality reviewer verifies:

- transaction correctness;
- migration replay and rollback safety;
- SQLite behavior;
- error handling;
- deterministic ordering;
- maintainability;
- duplication;
- test quality;
- absence of test-only production hooks.

The quality reviewer must not modify files.

### 3.6 Read-only Final Integration Reviewer

The final integration reviewer examines the complete subphase after all clusters pass.

It verifies:

- cross-cluster compatibility;
- full regression results;
- changed-file scope;
- protected files;
- migration and schema invariants;
- no leakage into later subphases;
- clean worktree;
- no push.

It must not modify files.

## 4. Review Status Protocol

Every reviewer returns exactly one status:

- `APPROVED`
- `APPROVED_WITH_NOTES`
- `CHANGES_REQUIRED`
- `BLOCKED`

`CHANGES_REQUIRED` must include:

- file and line;
- violated design or cluster contract;
- minimum required correction;
- tests that must be rerun.

The controller sends findings back to the same implementer.

The user is not asked to relay routine review findings.

## 5. Cluster Execution Model

For every cluster:

1. Controller prepares exact task and repository context.
2. Writable implementer performs TDD, implementation, tests, and commit.
3. Read-only spec reviewer checks design and scope compliance.
4. If required, the same implementer repairs spec findings.
5. Read-only quality reviewer checks implementation quality.
6. If required, the same implementer repairs quality findings.
7. Controller records cluster completion.
8. Next cluster begins.

The controller must not ask “should I continue?” between clusters.

## 6. Phase 3A Clusters

### A1 — Schema and Migration Foundations

Includes:

- test support and normalized schema snapshots;
- shared Phase 3A constants;
- migration preview;
- artifact business keys;
- revision output schema;
- revision approval status;
- approval action and evidence schema;
- Phase 2 compatibility updates.

### A2 — Approval, Review, and Validation Store APIs

Includes:

- approval record mapping;
- review tables;
- atomic review creation and events;
- deterministic review status;
- latest validation queries.

### A3 — Atomic Outputs and RuntimeStore Migration Integration

Includes:

- atomic Phase 3 output insertion;
- migration orchestrator;
- RuntimeStore legacy-open path;
- migration replay;
- rollback;
- foreign-key lifecycle;
- transient-table checks.

### A4 — Parity, Regression, and Acceptance

Includes:

- fresh-versus-migrated schema parity;
- Phase 0–2 regressions;
- full test suite;
- changed-file and protected-file checks.

A4 is acceptance-only. Production changes discovered in A4 return to the owning
earlier cluster.

## 7. Phase 3B–3E Cluster Pattern

### Phase 3B

- B1 Canonical model and schema
- B2 Validators and validation persistence
- B3 Regression and acceptance

### Phase 3C

- C1 Deterministic renderer
- C2 Candidate outputs and provenance
- C3 Bundle and integrity
- C4 Regression and acceptance

### Phase 3D

- D1 Review and qualification lifecycle
- D2 Approval and service orchestration
- D3 CLI
- D4 Regression and acceptance

### Phase 3E

- E1 Skill package and runtime entrypoint
- E2 Verifier
- E3 Verification reports
- E4 Final Phase 3 acceptance

The controller may refine cluster membership when repository evidence requires it,
provided design scope and public contracts do not change.

## 8. Limited Autonomous Repair Authority

The controller may repair and continue without user approval when the change does
not alter the frozen design.

Allowed autonomous repairs:

- imports and symbol paths;
- private helper naming, placement, and extraction;
- task file ownership and staging scope;
- focused-test commands;
- missing fixtures or test support;
- old-test compatibility changes that preserve existing behavior;
- internal commit grouping;
- type errors;
- SQLite syntax defects;
- transaction implementation details that preserve the frozen contract;
- plan corrections that record actual cluster ownership and execution order.

All autonomous plan deviations must be listed in the final report and reviewed by
the read-only spec reviewer.

## 9. Automatic Cluster Split

If a cluster remains blocked after repeated implementation and review cycles, the
controller may split that cluster once into smaller sequential subclusters.

Rules:

- maximum one automatic split per original cluster;
- scope may not expand;
- public contracts may not change;
- the split must be recorded in the plan deviation report;
- each new subcluster receives the same implementer/spec-review/quality-review cycle.

If the split cluster remains blocked, the controller triggers a Stop Condition.

## 10. Stop Conditions

The controller must stop and ask the user when any of the following occurs:

- the frozen Phase 3 Design must change;
- a public API, Canonical structure, approval meaning, or persistence contract must change;
- current subphase or cluster scope must expand beyond its authorized boundary;
- work would enter a later Phase 3 subphase before the current gate passes;
- work would enter Phase 4;
- two valid implementations produce materially different business behavior and tests
  cannot determine the intended result;
- migration may cause irreversible data loss;
- an existing test, schema, fixture, golden output, or acceptance gate would need to be weakened;
- full regression failures persist and their root cause is outside the current cluster;
- a cluster remains blocked after one automatic split;
- repository state is dirty or inconsistent in a way that prevents safe continuation;
- required evidence or source files are missing.

On a Stop Condition:

- stop implementation;
- do not commit partial work after the blocker;
- do not push;
- report exact evidence and the required user decision.

## 11. Plan Detail Policy

Subphase plans freeze:

- goals;
- inputs and outputs;
- public contracts;
- file boundaries;
- invariants;
- acceptance tests;
- stop conditions.

Plans should not attempt to freeze every private helper or full future code body.

Real code, real tests, and repository evidence are the authority for implementation
details that do not alter the frozen design.

## 12. Git and Worktree Rules

- Use one dedicated Phase 3 implementation worktree.
- Use one implementation branch per subphase unless the controller documents a safer
  alternative.
- Only one writable implementer operates in that worktree at a time.
- Read-only agents may inspect the same worktree.
- No automatic merge.
- No push.
- Keep the worktree clean at every completed cluster boundary.

## 13. Required Verification Per Cluster

Every production cluster must provide:

- failing focused test evidence;
- passing focused test evidence;
- related regressions;
- diff check;
- commit hash;
- changed-file list;
- spec review result;
- quality review result.

Acceptance-only clusters may begin green and must not introduce production behavior.

## 14. Required Verification Per Subphase

Every subphase completion requires:

- all cluster commits;
- all spec review results;
- all quality review results;
- focused test results;
- subphase regressions;
- full pytest result;
- schema or output parity checks where applicable;
- changed-file allowlist result;
- protected-file verification;
- clean worktree;
- no-push confirmation;
- final integration review.

## 15. Phase 3 Completion

Phase 3 is complete only when:

- 3A, 3B, 3C, 3D, and 3E all pass;
- the Phase 3 final verifier passes;
- verification reports are complete;
- no protected file changed without authorization;
- no Phase 4 behavior was implemented;
- the final integration reviewer returns `APPROVED`;
- the worktree is clean;
- no push occurred.

Required final status:

```text
PHASE_3_COMPLETE
PHASE_4_NOT_AUTHORIZED
```
