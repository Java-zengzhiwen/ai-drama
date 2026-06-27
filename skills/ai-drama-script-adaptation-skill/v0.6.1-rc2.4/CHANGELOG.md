# Changelog

## v0.6.1-rc2.4

- Adds isolated runtime reproduction support for the rc2.4 candidate workspace.
- Records reviewer-disagreement arbitration evidence and targeted repair closure.
- Records the FB01/FB16 fixes from arbitration while preserving generic, source-driven behavior.
- Keeps SCRIPT_APPROVAL state-neutral in the generic runtime package: candidates may remain pending user acceptance or record explicit script approval while formal integration stays on hold and downstream execution remains unauthorized.
- Keeps generic runtime behavior source-driven; no project-specific script facts, beat counts, scene counts, or dialogue are added to generic Skill files.

## v0.6.1-rc2.2

- Adds atomic core-story-beat extraction rules.
- Adds body evidence zone policy and validator enforcement.
- Adds emotional progression and causal coverage requirements.
- Adds source-claim-audit before drafting.
- Tightens coverage QC against scene-card scripts and metadata evidence.
- Adds self-contained skill rules.
- Adds CLI validators.
- Adds real Draft 2020-12 validation via jsonschema.
- Adds real mutation tests and a neutral validation set.
