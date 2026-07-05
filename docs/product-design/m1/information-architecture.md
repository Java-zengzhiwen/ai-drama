# M1 Information Architecture

## Routes

```text
/projects
/projects/:projectId
/projects/:projectId/chapters/:chapterId
```

Settings, assets, Shot Prompt, Agnes, result, and rerun routes are excluded from M1 design detail.

## Project List

Purpose: choose or create a production project.

Core content:

- project name;
- description;
- chapter count;
- last updated time;
- overall M1 progress;
- next action.

States:

- empty: no project yet;
- loading: project rows skeleton;
- error: project loading failed with retry;
- success: project rows available.

## Project Board

Purpose: scan one project and choose the next chapter action.

Core content:

- project metadata;
- production brief summary;
- chapter table;
- per-chapter status;
- blocking reason;
- next action.

Chapter statuses:

```text
source_empty
source_ready
script_draft
script_approved
storyboard_draft
storyboard_approved
blocked
error
```

## Chapter Workspace

Purpose: complete the M1 chapter workflow in one place.

Primary regions:

- project/chapter rail;
- workflow progress rail;
- tab bar;
- main editor/table area;
- right inspector;
- bottom pagination or revision utility area.

Tabs:

```text
原文
剧本
分镜
```

Later tabs may appear as locked labels only when needed for orientation, but M1 does not design their internal screens.
