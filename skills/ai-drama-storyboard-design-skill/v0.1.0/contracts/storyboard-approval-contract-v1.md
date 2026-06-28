# Storyboard Approval Contract v1

Storyboard approval is allowed only when:

1. the storyboard revision is derived from the current approved script revision;
2. all required storyboard validators ran and passed;
3. no required validator was incorrectly marked not applicable;
4. the source script approval record captured at generation time is preserved in provenance;
5. the storyboard revision is fresh against the current approved script revision.

Approval actions:

- `storyboard_approved`
- `storyboard_rejected`

Approval must not rewrite source provenance after later script approvals.
