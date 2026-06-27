---
name: ai-drama-script-adaptation-skill-v0.6.1-rc2.4
description: Self-contained generic skill for adapting source chapters into complete AI drama scripts with source-derived beat coverage, assumption/conflict governance, Draft 2020-12 schema validation, hash evidence, handoff contracts, and SCRIPT_APPROVAL creator presentation.
---

# AI Drama Script Adaptation Skill v0.6.1 RC2.4

## Purpose

Adapt one source chapter into a complete creator-readable drama script while preserving source facts, tracking assumptions, and blocking approval when mandatory source beats are missing or distorted.

## Scope

Use only for script adaptation and script approval preparation. Do not run character, scene, prop, visual, storyboard, image, video, platform execution, or downstream skills.

## Inputs

Require full source chapter, world/canon notes, character references, project brief, chapter scope policy if present, adaptation extension registry if present, and any approved creative-quality baseline. Missing optional inputs must be recorded.

## Authority Precedence

Source material and source-derived beat registry govern facts. Canon and project setup govern continuity. Approved creative baselines guide structure and readability only. Candidate extensions are not facts unless explicitly authorized.

## Source Material Loading

Read full source text before drafting. Do not draft from summaries alone. Record input refs and hashes in evidence outputs.

## Core Story Beat Extraction

Extract an atomic registry of source beats before scene writing. Each critical beat records id, importance, source evidence, required event, required information, required causal link, required relationship state, required emotional change, body evidence requirement, involved characters, visual anchors, and omission risk. Critical dimensional fields must be nonempty: use a concrete value such as `not_applicable: no relationship change in this beat` only when the dimension truly does not apply. Do not merge distinct dramatic functions to reduce beat count. Beat identifiers and counts are project data, never hardcoded by the skill.

## Creative Markdown Draft

Write complete creator-facing Markdown scenes before JSON. Each scene with critical beats must dramatize triggering event, immediate reaction, action/dialogue progression, emotional or relationship change, and new in-scene state. Metadata may exist, but it must not replace the readable script body.

## Fidelity Constraints

Critical beats may not be omitted or distorted. Character motivations, relationships, timeline, and unknown boundaries must follow the source authority stack.

## Adaptation Extension Policy

Default policy is exclude unapproved extensions. Read extension registry dynamically. Authorized extensions must be clearly marked; unauthorized extensions in the script are hard blockers.

## Production Assumption Classification

Every non-explicit filming, performance, environment, dialogue, continuity, motivation, or adaptation addition must be logged with classification, source support, and approval requirement.

## Source Conflict Resolution

Before drafting, run source-claim-audit across characters, objects, actions, relationships, and causal chains. When source wording conflicts or is ambiguous, create conflict registry items. Prefer later explicit event sequences, direct dialogue, and source-specific action over broad earlier implication. Record claims examined, potential conflicts, selected interpretation, resolution basis, impact, and whether user decision is required.

## Independent Coverage QC

After Markdown draft, evaluate every beat independently against body evidence zone text only. Scene goals, metadata, emotion labels, covered-beat declarations, coverage reports, JSON-only fields, and creator summaries cannot count as story evidence. Check event, information, causal, emotional, and relationship coverage separately. A beat is fully covered only when every applicable dimension has script-body evidence.

## Hard Blockers

Block approval for missing or distorted critical beat, motivation change, unauthorized factual invention, unauthorized extension, synopsis-only script, broken relationship comprehension, missing confession information, or unclassified assumption.

## Creative Revision Loop

If QC finds partial coverage or quality gaps, revise Markdown first. Regenerate JSON, hashes, handoff, and presentation after revision. Do not patch JSON without updating Markdown.

## JSON Serialization

Serialize only after Markdown passes content QC. JSON must preserve scene order, scene ids, characters, dialogue, covered beat ids, and full scene Markdown.

## Markdown/JSON Equivalence

Validate scene count, scene order, characters, dialogue, key lines, covered beats, and absence of JSON-only or Markdown-only story facts. `full_scene_markdown` must match the Markdown scene block exactly after trimming outer whitespace.

## Schema Validation

Use real Draft 2020-12 JSON Schema validation through `jsonschema>=4.23.0`. If the dependency is unavailable, fail clearly with `ERR_JSONSCHEMA_IMPORT`; do not fall back to vendored stubs or permissive facades. Schema checks are structural and separate from semantic coverage checks.

## Hash and Evidence

Compute hashes from current bytes. Artifact registry, sidecar, handoff, and review request must agree with real file hashes.

## Handoff Contract

Handoff must include project/chapter identifiers, artifact version, source fingerprint, input refs, output refs, validation refs, stale status, blocking issues, pending review status, current gate, and downstream approval false. Every input and output ref must include a current SHA256. Output refs must include `source_claim_audit`.

## SCRIPT_APPROVAL

Opening script approval never means approval. Gate remains pending until explicit user instruction. Approved-for-downstream must remain false before user approval.

## Creator Presentation

Approval presentation must include full script body, revision, scene overview, strict critical coverage, partial beats, assumptions, extensions, conflicts, current issues, recommendation, next stage, impact scope, and copyable user decisions. It must state `current_gate=SCRIPT_APPROVAL`, `approved_for_downstream=false`, and a clear gate status. Before user approval it must ask for SCRIPT_APPROVAL; after user approval it may record script acceptance, but it must not authorize downstream execution or formal integration.

## Revision Presentation

After revision, show complete revised script, diff, fixed items, unresolved items, coverage changes, new hashes, new revision, and next action.

## Draft/Approved Isolation

Draft artifacts and approved artifacts must remain separated. Never overwrite an approved artifact during draft repair.

## Failure Modes

If required evidence is missing, schema validation fails, coverage cannot be proven, or genericity fails, stop with a blocked status and do not proceed to downstream work.

## Required Outputs

Produce Markdown script, JSON script, beat registry, coverage report, assumption log, conflict registry, extension registry, source-claim-audit, schema validation report, artifact registry, evidence sidecar, handoff manifest, review request, creator presentation, and test reports.

## Prohibited Behaviors

Do not compress full scripts into synopsis, invent unknown facts, treat creative baseline as fact, hardcode project-specific names or beat ids in generic validators, approve gates, or run downstream skills.

## Genericity Requirements

All validators must read beat ids, critical sets, scene order, paths, and extension registries from input files. Generic skill code must not contain project-specific names, fixed beat counts, fixed scene counts, or sample chapter dialogue.





## RC2.4 Runtime Separation Addendum

Required references for every run: `references/atomic-core-story-beat-rules.md`, `references/body-evidence-policy.md`, `references/emotional-progression-rules.md`, and `references/creator-presentation-rules.md`. Run source-claim-audit before drafting. A technically valid schema/hash/handoff package fails creative reproduction if the creator-facing script is a scene card, if metadata is used as coverage evidence, if causal/emotional/relationship dimensions are missing, or if the creator presentation recommends approval without grounding in these checks. Runtime-only packages must include only runtime instructions, references, schemas, templates, contracts, validators, requirements, and top-level docs.
