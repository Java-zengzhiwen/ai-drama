# M3 Visual Tokens

M3 inherits M1 and M2 visual tokens. No new visual system is introduced.

## Color

```text
page.background        #f6f8fb
surface.default        #ffffff
surface.subtle         #f9fafc
border.default         #d9dee8
border.strong          #b8c0cc
text.primary           #1f2937
text.secondary         #5f6b7a
text.muted             #8a94a3
accent.focus           #2563eb
status.success         #16a34a
status.warning         #d97706
status.error           #dc2626
status.info.bg         #dbeafe
status.blocked.bg      #fff1f2
status.blocked.border  #fca5a5
```

## Typography

```text
font.family   Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
body.size     14px
body.line     1.45
label.size    12px
title.size    18px
heading.size  22px
```

## Spacing

```text
space.1  4px
space.2  8px
space.3  12px
space.4  16px
space.5  20px
space.6  24px
```

## Radius

```text
radius.sm  4px
radius.md  6px
radius.lg  8px
```

## Media Preview Sizes

```text
result.preview.video      16:9, fills inspector content width
result.version.thumbnail  16:9, min 96px wide
asset.ref.thumb           54px x 54px
shot.table.row            stable dense row height
drawer.width.desktop      360px to 420px
```

## State Mapping

```text
waiting       warning
queued        processing
submitting    processing
generating    processing
completed     success
failed        error
cancelled     default
result_expired warning
```

## Layout Rules

- Keep the generation table as one grouped surface with row separators.
- Keep result preview and rerun controls in inspector or drawer regions.
- Do not put cards inside cards.
- Use borders and subtle surface tints before shadows.
- Tables stay dense and horizontally scrollable.
- Drawers use the same form rhythm as M2 asset detail.
- Video preview is a decision surface, not an editing surface.
