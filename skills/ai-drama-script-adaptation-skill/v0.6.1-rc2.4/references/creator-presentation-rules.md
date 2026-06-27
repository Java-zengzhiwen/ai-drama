# Creator Presentation Rules

Display full script, revision, overview, coverage, assumptions, extensions, conflicts, issues, recommendation, next stage, impact scope, and copyable user commands.

The presentation must stop at SCRIPT_APPROVAL:

- `current_gate=SCRIPT_APPROVAL`
- `approved_for_downstream=false`
- `status` must clearly distinguish pre-approval review from post-approval script acceptance.

Do not imply downstream approval has happened. The only allowed next actions are explicit user choices such as `accept`, `request_revision`, or `reject`, and post-approval artifacts must still keep formal integration on hold unless separately authorized.
