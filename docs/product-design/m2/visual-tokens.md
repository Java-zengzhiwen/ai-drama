# M2 Visual Tokens

M2 inherits M1 visual tokens. No new visual system is introduced.

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

## Image Preview Sizes

```text
asset.tile.thumbnail     4:3, min 176px wide
asset.detail.preview     4:3, fills primary content column
asset.version.thumbnail  4:3, min 120px wide
asset.ref.thumb          54px x 54px
shot.keyframe.thumb      16:9
outfit.reference         3:4
```

## Layout Rules

- Asset review gives image preview the largest region.
- Tables remain dense and bordered like M1.
- Inspectors use labels above or label/value pairs.
- Major sections use dividers before elevation.
- Repeated asset tiles may use cards; page sections should not become nested cards.
- Locked M3 pages use disabled tab labels and inline lock reasons only.
