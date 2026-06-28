# Storyboard Workflow MVP Design

Date: 2026-06-28

## Goal

Add a first-class Storyboard Workflow MVP to the existing Script Skill Runtime without changing the approved Script Runtime data semantics.

## Source audit outcome

The SOURCE_ROOT audit found no trustworthy active Storyboard Skill package to migrate.
The only defensible path is to create a new formal skill:

- `skills/ai-drama-storyboard-design-skill/v0.1.0`

Provenance:
- `newly_created_from_approved_storyboard_requirements`

## Scope

In scope:
- Storyboard Design Skill package
- Storyboard Run
- Storyboard Revision
- Storyboard Validators
- Storyboard Approval
- Compare / Export
- Source staleness detection against the approved script revision

Out of scope:
- Shot Prompt Skill
- visual asset generation
- image generation
- video generation
- LibTV Adapter
- Agnes Adapter
- Web UI
- REST API
- agent runtime
- workflow engine generalization
- Script Skill business logic changes

## Runtime contract

Storyboard workflow is gated by an approved drama script revision.

Proposed state chain:
- `SCRIPT_APPROVED`
- `STORYBOARD_RUN_ALLOWED`
- `STORYBOARD_GENERATED`
- `STORYBOARD_VALIDATED`
- `STORYBOARD_APPROVED`

Source staleness:
- if the upstream approved script revision changes, the dependent storyboard revision becomes stale
- stale storyboard revisions must not continue to downstream approval/export paths

## Package shape

Create a new skill package under:
- `skills/ai-drama-storyboard-design-skill/v0.1.0/`

Expected package contents:
- `SKILL.md`
- `README.md`
- `CHANGELOG.md`
- `MIGRATION-NOTES.md`
- `requirements.txt`
- `contracts/`
- `schemas/`
- `validators/`
- `templates/`
- `references/`
- `skill.json`

## Data model

Storyboard artifacts should mirror the runtime style used by the Script MVP:
- immutable storyboard revision artifact
- explicit provenance and upstream script revision binding
- validator inventory
- approval artifacts
- compare/export support

Storyboard-specific content should emphasize:
- shot grouping
- scene intent
- camera framing
- composition continuity
- prop continuity
- no downstream execution syntax

## Validation philosophy

Validators should reject:
- storyboard created without an approved upstream script revision
- storyboard package that references stale upstream script content
- storyboard artifacts that leak Shot Prompt or LibTV execution detail
- storyboard artifacts that omit provenance or upstream binding

Validators should pass only when the package remains source-grounded, revision-bound, and self-consistent.

## Implementation strategy

1. Create the new storyboard skill package skeleton.
2. Add formal package metadata and scope boundaries.
3. Define storyboard schemas/contracts/templates.
4. Implement validators and registration.
5. Add runtime-level tests for package discovery, gating, staleness, and validator behavior.
6. Wire compare/export paths after the package and tests exist.

## Acceptance criteria

- The repo contains a formal Storyboard Skill package at `skills/ai-drama-storyboard-design-skill/v0.1.0`
- The package is clearly separate from Script Adaptation
- The package does not depend on Shot Prompt, LibTV, image, or video execution
- The runtime can detect storyboard staleness from upstream script revision changes
- Storyboard approval is blocked until the upstream script is approved and current
