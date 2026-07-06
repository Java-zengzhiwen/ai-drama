# Shot Prompt Contract v1

## Canonical Boundary

The Shot Prompt Skill emits `shot_prompt_set` only. It transforms approved
storyboard facts and approved asset references into prompt text and continuity
instructions. It does not persist revisions, decide readiness gates, call Agnes
video, build LibTV execution packages, or produce post-production packages.

## Required Mapping

- The output must contain one shot prompt for each source storyboard shot.
- Each prompt must preserve the source `shot_id`, `shot_order`,
  `duration_seconds`, `scene_id`, character IDs, prop IDs, dialogue intent, and
  continuity facts.
- Prompt additions must be cinematic expression only. They must not introduce
  new plot facts or change source facts.

## Required Prompt Fields

Every shot must include:

- non-empty `positive_prompt`;
- non-empty `negative_prompt`;
- non-empty `asset_refs`;
- continuity notes that preserve scene, character, prop, costume, lighting, and
  camera-direction consistency;
- provider-neutral Agnes video preview parameters only.

## Unsupported Outputs

The following outputs are explicitly unsupported in this package:

- `libtv_execution_package`
- `post_production_package`

## Validator Contract

`validators/validate_shot_prompt_set.py` reads canonical JSON from
`--revision`, writes a JSON report to `--report`, and imports
`ai_drama_runtime.shot_prompt_canonical` from `--repo-root`.

Exit code `0` means PASS. Any canonical or consistency failure must exit
nonzero and write a report with `status` set to `FAIL`.
