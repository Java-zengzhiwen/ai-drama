# AI Drama Shot Prompt Skill v0.1.0

Create a provider-neutral `shot_prompt_set` from an approved canonical
storyboard and approved asset references. This skill is limited to canonical
prompt content for Milestone 2 Shot Prompt Studio.

## Scope

- Produce exactly one shot prompt entry for each source storyboard shot.
- Preserve source shot identity, shot order, duration, dialogue intent, and
  continuity facts.
- Include positive and negative prompts for every shot.
- Include asset references for every shot. Asset references must identify
  approved visual assets supplied by the runtime input assembly step.
- Keep prompt content provider-neutral. Agnes video parameters may be included
  only as preview metadata.

## Required Output

The only supported output is `shot_prompt_set` using profile
`shot-prompt-canonical-v1` and parser `shot-prompt-canonical-json-v1`.

Unsupported outputs:

- `libtv_execution_package`
- `post_production_package`

## Consistency Rules

The generated set must maintain stable character, scene, prop, costume,
lighting, camera-direction, and continuity language across shots. A prompt may
add cinematic phrasing, but it must not invent new facts, change dialogue,
change shot duration, remove required assets, or alter shot identity.

## Validation

Run the declared validator against the canonical JSON file:

```bash
python3 validators/validate_shot_prompt_set.py \
  --revision path/to/shot-prompt-set.json \
  --report path/to/report.json \
  --repo-root path/to/repo
```

The validator writes a JSON report with `status` set to `PASS` or `FAIL`.
