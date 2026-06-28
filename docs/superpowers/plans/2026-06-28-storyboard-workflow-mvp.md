# Storyboard Workflow MVP Plan

Date: 2026-06-28

## Plan

1. Create Storyboard Skill package skeleton at `skills/ai-drama-storyboard-design-skill/v0.1.0/`.
2. Add package metadata, scope boundaries, and migration notes.
3. Define storyboard contracts, schemas, templates, and validator entry points.
4. Add runtime tests for package discovery and Storyboard gating/staleness behavior.
5. Implement minimal runtime support for storyboard artifact registration, revision compare, export, and approval flow.
6. Run targeted verification and keep existing script runtime behavior unchanged.

## Hard boundaries

- Do not modify SOURCE_ROOT.
- Do not change Script Runtime business semantics.
- Do not add Shot Prompt, LibTV, image, video, or visual generation logic.
- Do not claim storyboard approval for stale or unapproved upstream scripts.

## Test strategy

- Start with package presence and metadata tests.
- Add fail-first tests for storyboard gating and staleness.
- Add validator registration tests.
- Add compare/export behavior tests only after artifact model exists.

## Deliverable order

1. Storyboard source audit document
2. Storyboard design spec
3. Storyboard implementation plan
4. Storyboard package scaffold
5. Runtime tests
6. Runtime implementation
7. Verification and commit
