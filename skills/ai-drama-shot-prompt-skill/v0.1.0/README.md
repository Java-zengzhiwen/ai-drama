# AI Drama Shot Prompt Skill v0.1.0

This package defines the Milestone 2 canonical Shot Prompt Skill package.

It accepts runtime-assembled storyboard facts and approved asset references,
then emits one `shot_prompt_set` JSON document. The package does not execute
runtime jobs, call provider APIs, generate Agnes video, build LibTV packages, or
perform post-production.

The active execution profile is:

- profile: `shot-prompt-canonical-v1`
- output: `shot_prompt_set`
- parser: `shot-prompt-canonical-json-v1`

The required validator is `shot_prompt_set_structure`, implemented at
`validators/validate_shot_prompt_set.py`.
