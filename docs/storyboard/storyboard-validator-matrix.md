# Storyboard Validator Matrix

| validator | required | applies_to | responsibility |
|---|---|---|---|
| storyboard_structure | yes | storyboard_revision | validate scene / shot structure and required shot fields |
| storyboard_duration | yes | storyboard_revision | validate 5-15 second duration bounds per shot |
| storyboard_source_coverage | yes | storyboard_revision | validate scene coverage against source scene references |
| storyboard_continuity | yes | storyboard_revision | validate continuity_in / continuity_out / blocking fields per shot |
| genericity | no | skill_package | scan package text for forbidden downstream terms |

## Runtime notes

- Required validators must execute for storyboard revisions.
- `NOT_APPLICABLE` is only valid when the manifest explicitly marks the profile as not applicable.
- Validator reports and stdout/stderr are persisted for every run.
