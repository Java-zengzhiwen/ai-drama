# M1 Interaction Spec

## Navigation

The user moves through three surfaces:

1. Project list.
2. Project board.
3. Chapter workspace.

Project and chapter switching must preserve unsaved-edit warnings inside the current tab. The prototype models this as local state only.

## Workflow Rail

Steps:

```text
原文完成 -> 剧本已确认 -> 分镜待确认/已确认
```

Rules:

- completed steps use success styling;
- current step uses focused styling;
- blocked steps show a lock state and a concise reason;
- later M1-external steps are not expanded.

## Source Tab

Actions:

- edit source text;
- save as a new source revision;
- show save success, loading, and error states.

Empty state:

```text
暂无小说原文。粘贴正文后才能生成剧本。
```

## Script Tab

Actions:

- generate script from saved source;
- edit script;
- save as new revision;
- run validation;
- confirm script;
- reject revision.

Gate behavior:

- pending or rejected script blocks storyboard generation;
- approved script unlocks storyboard generation.

## Storyboard Tab

Actions:

- generate storyboard after script approval;
- select a shot row;
- edit shot fields in the inspector;
- save as new revision;
- run validation;
- confirm storyboard;
- reject revision.

Canonical fields shown in the table:

```text
shot_order
duration_seconds
shot_size
camera_angle
camera_movement
visual_composition
character_positions
dialogue
continuity_in
continuity_out
```

## Confirmation Gates

Script confirmation:

- primary action: `确认剧本`;
- success result: `script_approved`;
- failure result: validation error or rejected revision message.

Storyboard confirmation:

- primary action: `确认分镜`;
- success result: `storyboard_approved`;
- failure result: validation error, missing script approval, or invalid canonical fields.

## Prototype Controls

The prototype includes local controls for:

- switching project list, project board, and chapter workspace;
- switching source/script/storyboard tabs;
- selecting storyboard rows;
- toggling simulated view states;
- simulating an unapproved script block;
- confirming the storyboard.
