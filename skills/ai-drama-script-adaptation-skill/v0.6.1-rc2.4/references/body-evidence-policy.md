# Body Evidence Policy

Coverage evidence must come only from the creator-facing script body. The body evidence zone is the portion of each scene that contains performed story material, not planning metadata.

Allowed evidence:

- actions that actually occur in the script body
- spoken dialogue
- performable reactions, gestures, breath, gaze, micro-expression, posture, or physical response
- effective silence paired with character reaction
- real scene-ending actions or state changes that happen inside the scene

Forbidden evidence:

- scene goal
- emotion-start, emotion-progression, or emotion-end labels
- atmosphere labels
- metadata bullets or table fields
- covered-beat declarations
- coverage report conclusions
- QC notes
- creator-presentation summaries
- JSON-only fields not present in the creator-facing body
- Markdown-only story facts not serialized into the matching JSON scene block

Coverage generation and validators must use the same boundary. If evidence appears only in metadata, the beat is not covered.
Markdown and JSON must carry the same story facts. If a scene body line appears only in Markdown or only in JSON, revise the artifact pair and regenerate hashes before handoff.

Recommended scene body headings that belong to the body evidence zone:

- `### 剧本正文`
- `### 动作`
- `### 台词`
- `### 表演反应`
- `### 停顿、呼吸、视线、微表情`
- `### 声音或有效沉默`
- `### 场尾钩子`
- `### 场次结束动作`

Headings and labels alone are not evidence. The evidence must be a concrete line of story material under an allowed body heading.
