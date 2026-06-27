# Atomic Core Story Beat Rules

Core Story Beats must be atomic units of dramatic function. Do not mechanically merge distinct functions into one beat merely because they appear in the same paragraph.

A beat must not combine these functions when they can be independently verified:

- relationship fact
- external event
- key information
- causal explanation
- character choice
- emotional turn
- relationship state change
- chapter-ending hook

When a source passage contains an action chain such as:

```text
action -> reason -> guilt -> understanding -> decision
```

extract multiple independently checkable beats. Beat count is source-derived and must not be preset, capped, or reduced to make coverage easier.

Every critical beat must include these fields with nonempty values. If a dimension truly does not apply, write an explicit `not_applicable: <reason>` value rather than leaving the field blank:

```json
{
  "required_event": "concrete action or not_applicable: reason",
  "required_information": "concrete information or not_applicable: reason",
  "required_causal_link": "cause/effect or not_applicable: reason",
  "required_relationship_state": "relationship state/change or not_applicable: reason",
  "required_emotional_change": "emotional movement or not_applicable: reason",
  "body_evidence_requirement": "what must be visible in script body"
}
```

Critical coverage requires proof for each nonempty field. A single result line cannot cover a causal explanation, emotional transition, and relationship state change unless the script body actually dramatizes all three.
