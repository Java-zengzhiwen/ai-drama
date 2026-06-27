# Migration Notes

Do not install into formal release until formal integration is explicitly authorized. Keep SCRIPT_APPROVAL, formal integration, and downstream execution separate.

Runtime projects must remain pending until explicit user approval is recorded by the parent orchestrator. A candidate awaiting user review should use:
- `candidate_approval_status = pending_user_acceptance`
- `process_revision_status = completed`
- `formal_integration_status = hold`
- `current_gate = SCRIPT_APPROVAL`
- `approved_for_downstream = false`

The runtime-only package is for isolated reproduction and deterministic validation only. Downstream execution remains unauthorized: do not run Character Bible, Scene Bible, Prop Bible, Visual Anchor, Scene Stabilization, Image Prompt, Storyboard, Shot Prompt, LibTV, image, or video stages from this package. The formal release has not yet been integrated.
