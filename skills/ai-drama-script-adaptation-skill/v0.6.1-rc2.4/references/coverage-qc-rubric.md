# Coverage QC Rubric

Statuses: `fully_covered`, `partially_covered`, `missing`, `distorted`. Partial never counts as strict full coverage.

Evidence must be in the script body evidence zone. Metadata, scene goals, emotion labels, coverage conclusions, and creator-presentation summaries do not count.

For every beat, evaluate these dimensions separately:

- event coverage
- information coverage
- causal coverage
- emotional coverage
- relationship coverage

For critical beats, every nonempty required dimension from the beat registry must be fully covered by body evidence. If one dimension is missing, the beat is not strictly fully covered.

Coverage reports must include body evidence refs and must not use field labels, `Covered Beats`, scene goals, or QC prose as evidence.
