# Storyboard Source Audit

Audit target:
- `SOURCE_ROOT=/Users/zengzhiwen/AI-manju/ai-drama-script-agent-lab`

Audit date:
- 2026-06-28

## Scope

I searched SOURCE_ROOT for:
- `ai-drama-storyboard-design-skill`
- `storyboard-design`
- `storyboard`
- `导演分镜`
- `分镜设计`
- `SKILL.md`
- `manifest`
- `contracts`
- `schemas`
- `validators`
- `fixtures`
- `reports`
- `v0.5`
- `v0.6`
- `Wave 4`
- `Batch 3`

I also checked the most plausible nearby artifact families:
- script skill packages under `04-work/`
- runtime-only reproduction packages under `05-live-reproduction/`
- visual preapproval and scene stabilization outputs under `02-current-candidate/`
- visual reports under `07-reports/`

## Findings

### Candidate 1: `04-work/ai-drama-script-adaptation-skill-v0.6.1-rc2.4/`
- Source path: `04-work/ai-drama-script-adaptation-skill-v0.6.1-rc2.4/SKILL.md`
- Declared version: `v0.6.1-rc2.4`
- Active version: yes, but for Script Adaptation only
- Full `SKILL.md`: yes
- Contract files: yes
- Schema files: yes
- Validator files: yes
- Dependency on Shot Prompt / LibTV / visual assets: no, it explicitly forbids storyboard and downstream stages
- Formal Skill or report/fixture: formal Skill package, but not Storyboard
- Credible storyboard migration candidate: no

Decision:
- Rejected as storyboard source. The package scope is script adaptation only, and its own `SKILL.md` explicitly excludes storyboard, image, video, and downstream execution.

### Candidate 2: `05-live-reproduction/v0.6.1-rc2.4-isolated-reproduction/runtime/`
- Source path: `05-live-reproduction/v0.6.1-rc2.4-isolated-reproduction/runtime/SKILL.md`
- Declared version: `v0.6.1-rc2.4`
- Active version: no, runtime-only reproduction package
- Full `SKILL.md`: yes
- Contract files: yes
- Schema files: yes
- Validator files: yes
- Dependency on Shot Prompt / LibTV / visual assets: no, but it explicitly forbids downstream stages
- Formal Skill or report/fixture: runtime-only package
- Credible storyboard migration candidate: no

Decision:
- Rejected. This package is an isolated reproduction/runtime support package for script adaptation, not an active storyboard skill.

### Candidate 3: `05-live-reproduction/second-live-reproduction-r3/runtime/`
- Source path: `05-live-reproduction/second-live-reproduction-r3/runtime/SKILL.md`
- Declared version: reproduction variant
- Active version: no
- Full `SKILL.md`: yes
- Contract files: yes
- Schema files: yes
- Validator files: yes
- Dependency on Shot Prompt / LibTV / visual assets: no, but downstream storyboard is forbidden
- Formal Skill or report/fixture: runtime-only reproduction package
- Credible storyboard migration candidate: no

Decision:
- Rejected for the same reason as Candidate 2.

### Candidate 4: `02-current-candidate/chapter-001-v0.6.1-rc2.4/visual-preapproval/`
- Source path family:
  - `visual-preapproval/scene-stabilization/scene-stabilization-handoff-manifest.json`
  - `visual-preapproval/image-prompts/*.md|*.json`
  - `visual-preapproval/p0-test-assets/*.png`
  - `visual-preapproval/visual-anchors/*.md|*.json`
- Declared version: `v0.6.1-rc2.4`
- Active version: no; these are candidate artifacts for a chapter, not a reusable skill package
- Full `SKILL.md`: no
- Contract files: partial, but not a Skill package contract set
- Schema files: no formal storyboard skill schemas
- Validator files: no storyboard validators
- Dependency on Shot Prompt / LibTV / visual assets: yes, directly tied to visual generation, scene stabilization, and image-prompt work
- Formal Skill or report/fixture: candidate artifacts and manifests
- Credible storyboard migration candidate: no

Decision:
- Rejected. This family is downstream visual planning and P0 asset material, not a storyboard-design skill.

### Candidate 5: `07-reports/visual-p0-v0.6.1-rc2.4/`
- Source path family:
  - `visual-human-review-report.*`
  - `scene-stabilization-verification.*`
  - `visual-asset-completion-qc.*`
- Declared version: `v0.6.1-rc2.4`
- Active version: no
- Full `SKILL.md`: no
- Contract files: no
- Schema files: no
- Validator files: no
- Dependency on Shot Prompt / LibTV / visual assets: yes, report-only evidence for visual approval
- Formal Skill or report/fixture: reports
- Credible storyboard migration candidate: no

Decision:
- Rejected. Reports are evidence artifacts, not an active skill package.

## Negative evidence

I found no trustworthy active Storyboard Skill package in SOURCE_ROOT:
- no `ai-drama-storyboard-design-skill` package directory
- no `storyboard-design` package with a matching `SKILL.md`
- no standalone storyboard contracts, schemas, and validators bundled as an active package
- no activity that can be trusted as a formal storyboard baseline without inheriting shot-prompt or visual-asset coupling

## Final decision

Decision: **new build**

Reason:
- The only real skill packages I found are script-adaptation or runtime-reproduction packages.
- Storyboard-related artifacts in SOURCE_ROOT are downstream candidate assets, scene stabilization outputs, or reports.
- None of them provide a clean, source-independent, formally active Storyboard Skill that can be migrated without importing excluded downstream coupling.

Target package to create:
- `skills/ai-drama-storyboard-design-skill/v0.1.0`

Provenance:
- `newly_created_from_approved_storyboard_requirements`

## Notes for downstream implementation

- Keep Storyboard separate from Shot Prompt, LibTV, visual asset generation, and video workflows.
- Preserve provenance for any future migration candidates, but do not pretend the current audit found one.
- Use the script-approved revision as the upstream gate for Storyboard workflow.
- GitHub review can only verify this written audit; it cannot re-verify the local SOURCE_ROOT contents from the repository alone.
