# Resizable Source And Script Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the source, live script, failed script, and formal script views share one full-viewport, percentage-based, globally resizable three-pane workspace without changing backend generation semantics.

**Architecture:** Add a pure pane-ratio contract and one shared `ResizableChapterWorkspace` component. `SourceTab` and `ScriptTab` provide business-specific left, center, and right content while `ChapterWorkspace` owns the fixed viewport shell and compact workflow gate. Persist one versioned ratio preference in browser local storage, clamp it per breakpoint, and use Ant Design drawers below 1024px.

**Tech Stack:** React 18, TypeScript 5.7, Ant Design 5, TanStack Query, Vitest, Testing Library, Playwright, CSS Grid.

---

## Preconditions And Safety

- Authoritative design: `docs/superpowers/specs/2026-07-22-resizable-script-workspace-design.md`.
- Start implementation from the latest approved integration base, not from the documentation branch unless the user explicitly requests otherwise.
- Do not modify Python, database, supplier, Worker, SSE, Skill, or Revision contracts.
- Do not issue any real Provider request. Unit and E2E tests must use the existing mocked/fake network paths.
- Preserve existing script idempotency, stream recovery, partial-draft retention, validation, approval, and rejection behavior.
- Use TDD for every task and keep one focused commit per task.

## File Responsibility Map

### New files

| File | Responsibility |
|---|---|
| `web/src/features/chapter/workspaceLayout.ts` | Pure breakpoint, ratio, clamping, movement, parsing, and serialization contract. |
| `web/src/features/chapter/workspaceLayout.test.ts` | Exhaustive unit tests for ratio math and stored preference validation. |
| `web/src/features/chapter/useWorkspacePaneRatios.ts` | React state, viewport tracking, local-storage recovery, preview, and commit behavior. |
| `web/src/features/chapter/ResizableChapterWorkspace.tsx` | Shared desktop grid, separators, keyboard control, reset behavior, and compact drawers. |
| `web/src/features/chapter/ResizableChapterWorkspace.test.tsx` | Component tests for dragging, persistence, keyboard control, reset, and compact mode. |
| `web/src/features/chapter/ChapterNavigator.tsx` | Reusable chapter search/list/navigation pane used by source and script tabs. |
| `web/src/features/chapter/ChapterNavigator.test.tsx` | Navigation, search, current state, and route tests. |
| `web/src/features/chapter/WorkflowGateBar.tsx` | Compact blocker summary with on-demand details. |
| `web/src/features/chapter/WorkflowGateBar.test.tsx` | Compact, expand, collapse, and accessible-state tests. |

### Modified files

| File | Responsibility of change |
|---|---|
| `web/src/features/chapter/ChapterWorkspace.tsx` | Mark editor tabs as full-viewport and replace large lock alerts with `WorkflowGateBar`. |
| `web/src/features/chapter/SourceTab.tsx` | Remove embedded navigator state and render source content through the shared workspace. |
| `web/src/features/script/ScriptTab.tsx` | Render live, failed, empty, and formal script states through the same shared workspace. |
| `web/src/features/script/ScriptTab.test.tsx` | Preserve workflow behavior and assert stable three-pane layout across state transitions. |
| `web/src/app/app.css` | Full-viewport height chain, percentage grid, separators, internal scrolling, compact inspectors, and drawers. |
| `web/src/test/setup.ts` | Deterministic pointer and geometry support needed by focused tests. |
| `web/tests/script-streaming.spec.ts` | Layout, persistence, viewport, scrolling, and screenshot acceptance using mocked SSE. |

## Task 1: Freeze The Pane Ratio Contract

**Files:**
- Create: `web/src/features/chapter/workspaceLayout.ts`
- Create: `web/src/features/chapter/workspaceLayout.test.ts`

- [x] **Step 1: Write the failing ratio tests**

Create `web/src/features/chapter/workspaceLayout.test.ts`:

```ts
import { describe, expect, test } from "vitest";
import {
  WORKSPACE_RATIO_STORAGE_KEY,
  centerRatio,
  clampPaneRatios,
  defaultPaneRatios,
  moveDivider,
  parseStoredPaneRatios,
  serializePaneRatios,
} from "./workspaceLayout";

describe("workspace pane ratios", () => {
  test("uses approved percentage defaults", () => {
    expect(defaultPaneRatios(1920)).toEqual({ left: 11, right: 16 });
    expect(defaultPaneRatios(1180)).toEqual({ left: 14, right: 20 });
    expect(defaultPaneRatios(768)).toEqual({ left: 0, right: 0 });
    expect(WORKSPACE_RATIO_STORAGE_KEY).toBe("ai-drama:workspace-pane-ratios:v1");
  });

  test("keeps both side panes legal and the center at least 55 percent", () => {
    expect(clampPaneRatios({ left: 30, right: 30 }, 1920)).toEqual({ left: 20, right: 25 });
    expect(centerRatio(clampPaneRatios({ left: 30, right: 30 }, 1920))).toBe(55);
    expect(clampPaneRatios({ left: 2, right: 4 }, 1920)).toEqual({ left: 8, right: 12 });
  });

  test("moves the selected divider while preserving the opposite pane", () => {
    expect(moveDivider({ left: 11, right: 16 }, "left", 4, 1920)).toEqual({ left: 15, right: 16 });
    expect(moveDivider({ left: 11, right: 16 }, "right", 4, 1920)).toEqual({ left: 11, right: 12 });
    expect(centerRatio(moveDivider({ left: 20, right: 25 }, "left", 9, 1920))).toBe(55);
  });

  test("round trips one global versioned preference", () => {
    const encoded = serializePaneRatios({ left: 12.5, right: 17.5 });
    expect(parseStoredPaneRatios(encoded)).toEqual({ left: 12.5, right: 17.5 });
  });

  test.each([
    null,
    "",
    "not-json",
    JSON.stringify({ version: 2, left: 11, right: 16 }),
    JSON.stringify({ version: 1, left: "11", right: 16 }),
  ])("rejects invalid stored preferences: %s", (raw) => {
    expect(parseStoredPaneRatios(raw)).toBeNull();
  });
});
```

- [x] **Step 2: Run the test and verify the expected red state**

```bash
npm --prefix web run test -- --run src/features/chapter/workspaceLayout.test.ts
```

Expected: FAIL because `workspaceLayout.ts` does not exist.

- [x] **Step 3: Implement the pure ratio contract**

Create `web/src/features/chapter/workspaceLayout.ts`:

```ts
export type PaneRatios = Readonly<{ left: number; right: number }>;
export type WorkspaceDivider = "left" | "right";
type StoredPaneRatios = PaneRatios & { version: 1 };

export const WORKSPACE_RATIO_STORAGE_KEY = "ai-drama:workspace-pane-ratios:v1";
export const MIN_CENTER_RATIO = 55;
export const MIN_LEFT_RATIO = 8;
export const MAX_LEFT_RATIO = 20;
export const MIN_RIGHT_RATIO = 12;
export const MAX_RIGHT_RATIO = 28;

export function defaultPaneRatios(viewportWidth: number): PaneRatios {
  if (viewportWidth < 1024) return { left: 0, right: 0 };
  if (viewportWidth < 1440) return { left: 14, right: 20 };
  return { left: 11, right: 16 };
}

export function centerRatio(ratios: PaneRatios) {
  return roundRatio(100 - ratios.left - ratios.right);
}

export function clampPaneRatios(input: PaneRatios, viewportWidth: number): PaneRatios {
  if (viewportWidth < 1024) return { left: 0, right: 0 };
  let left = clamp(finiteOr(input.left, MIN_LEFT_RATIO), MIN_LEFT_RATIO, MAX_LEFT_RATIO);
  let right = clamp(finiteOr(input.right, MIN_RIGHT_RATIO), MIN_RIGHT_RATIO, MAX_RIGHT_RATIO);
  let overflow = left + right - (100 - MIN_CENTER_RATIO);
  if (overflow > 0) {
    const rightReduction = Math.min(overflow, right - MIN_RIGHT_RATIO);
    right -= rightReduction;
    overflow -= rightReduction;
  }
  if (overflow > 0) left -= Math.min(overflow, left - MIN_LEFT_RATIO);
  return { left: roundRatio(left), right: roundRatio(right) };
}

export function moveDivider(current: PaneRatios, divider: WorkspaceDivider, delta: number, viewportWidth: number) {
  const candidate = divider === "left"
    ? { left: current.left + delta, right: current.right }
    : { left: current.left, right: current.right - delta };
  return clampPaneRatios(candidate, viewportWidth);
}

export function parseStoredPaneRatios(raw: string | null): PaneRatios | null {
  if (!raw) return null;
  try {
    const value = JSON.parse(raw) as Partial<StoredPaneRatios>;
    if (value.version !== 1 || !Number.isFinite(value.left) || !Number.isFinite(value.right)) return null;
    return { left: Number(value.left), right: Number(value.right) };
  } catch {
    return null;
  }
}

export function serializePaneRatios(ratios: PaneRatios) {
  return JSON.stringify({ version: 1, left: ratios.left, right: ratios.right } satisfies StoredPaneRatios);
}

function finiteOr(value: number, fallback: number) {
  return Number.isFinite(value) ? value : fallback;
}
function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(maximum, Math.max(minimum, value));
}
function roundRatio(value: number) {
  return Math.round(value * 100) / 100;
}
```

- [x] **Step 4: Run the focused test**

```bash
npm --prefix web run test -- --run src/features/chapter/workspaceLayout.test.ts
```

Expected: PASS.

- [x] **Step 5: Commit the ratio contract**

```bash
git add web/src/features/chapter/workspaceLayout.ts web/src/features/chapter/workspaceLayout.test.ts
git commit -m "feat: add chapter workspace ratio contract"
```

## Task 2: Build The Shared Resizable Workspace

**Files:**
- Create: `web/src/features/chapter/useWorkspacePaneRatios.ts`
- Create: `web/src/features/chapter/ResizableChapterWorkspace.tsx`
- Create: `web/src/features/chapter/ResizableChapterWorkspace.test.tsx`
- Modify: `web/src/app/app.css`
- Modify: `web/src/test/setup.ts`

- [x] **Step 1: Add deterministic pointer primitives to test setup**

Append to `web/src/test/setup.ts` while preserving network denial and existing `matchMedia` behavior:

```ts
Object.defineProperty(HTMLElement.prototype, "setPointerCapture", {
  configurable: true,
  value: () => undefined,
});
Object.defineProperty(HTMLElement.prototype, "releasePointerCapture", {
  configurable: true,
  value: () => undefined,
});
```

- [x] **Step 2: Write failing component tests**

Create `web/src/features/chapter/ResizableChapterWorkspace.test.tsx` with these cases:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { WORKSPACE_RATIO_STORAGE_KEY } from "./workspaceLayout";
import { ResizableChapterWorkspace } from "./ResizableChapterWorkspace";

function renderWorkspace() {
  return render(
    <ResizableChapterWorkspace
      center={<div>中央剧本</div>}
      left={<div>章节列表</div>}
      leftDrawerTitle="章节导航"
      right={<div>生成状态</div>}
      rightDrawerTitle="剧本详情"
    />,
  );
}

describe("ResizableChapterWorkspace", () => {
  beforeEach(() => {
    localStorage.clear();
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1920, writable: true });
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
      bottom: 500, height: 500, left: 0, right: 1000, top: 0, width: 1000,
      x: 0, y: 0, toJSON: () => ({}),
    });
  });

  test("starts at 11/73/16", () => {
    renderWorkspace();
    const workspace = screen.getByTestId("resizable-chapter-workspace");
    expect(workspace.style.getPropertyValue("--workspace-left")).toBe("11fr");
    expect(workspace.style.getPropertyValue("--workspace-center")).toBe("73fr");
    expect(workspace.style.getPropertyValue("--workspace-right")).toBe("16fr");
  });

  test("persists keyboard changes and resets on double click", () => {
    renderWorkspace();
    const divider = screen.getByRole("separator", { name: "调整章节导航宽度" });
    fireEvent.keyDown(divider, { key: "ArrowRight" });
    expect(screen.getByTestId("resizable-chapter-workspace").style.getPropertyValue("--workspace-left")).toBe("12fr");
    expect(JSON.parse(localStorage.getItem(WORKSPACE_RATIO_STORAGE_KEY) ?? "{}")).toMatchObject({ left: 12 });
    fireEvent.doubleClick(divider);
    expect(screen.getByTestId("resizable-chapter-workspace").style.getPropertyValue("--workspace-left")).toBe("11fr");
  });

  test("restores one global preference", () => {
    localStorage.setItem(WORKSPACE_RATIO_STORAGE_KEY, JSON.stringify({ version: 1, left: 13, right: 18 }));
    renderWorkspace();
    expect(screen.getByTestId("resizable-chapter-workspace").style.getPropertyValue("--workspace-left")).toBe("13fr");
  });

  test("uses center-first drawers below 1024px", () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 768, writable: true });
    renderWorkspace();
    expect(screen.getByText("中央剧本")).toBeVisible();
    expect(screen.getByRole("button", { name: "打开章节导航" })).toBeVisible();
    expect(screen.getByRole("button", { name: "打开剧本详情" })).toBeVisible();
    expect(screen.queryByRole("separator")).not.toBeInTheDocument();
  });
});
```

- [x] **Step 3: Run the component test and verify red**

```bash
npm --prefix web run test -- --run src/features/chapter/ResizableChapterWorkspace.test.tsx
```

Expected: FAIL because the hook and component do not exist.

- [x] **Step 4: Implement the ratio hook**

Create `web/src/features/chapter/useWorkspacePaneRatios.ts`:

```ts
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  WORKSPACE_RATIO_STORAGE_KEY,
  clampPaneRatios,
  defaultPaneRatios,
  parseStoredPaneRatios,
  serializePaneRatios,
  type PaneRatios,
} from "./workspaceLayout";

export function useWorkspacePaneRatios() {
  const [viewportWidth, setViewportWidth] = useState(() => window.innerWidth);
  const [rawRatios, setRawRatios] = useState<PaneRatios>(() =>
    parseStoredPaneRatios(localStorage.getItem(WORKSPACE_RATIO_STORAGE_KEY))
      ?? defaultPaneRatios(window.innerWidth),
  );
  useEffect(() => {
    const update = () => setViewportWidth(window.innerWidth);
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);
  const ratios = useMemo(() => clampPaneRatios(rawRatios, viewportWidth), [rawRatios, viewportWidth]);
  const preview = useCallback((next: PaneRatios) => setRawRatios(next), []);
  const commit = useCallback((next: PaneRatios) => {
    setRawRatios(next);
    try {
      localStorage.setItem(WORKSPACE_RATIO_STORAGE_KEY, serializePaneRatios(next));
    } catch {
      // The in-memory workspace remains usable when storage is unavailable.
    }
  }, []);
  const reset = useCallback(() => commit(defaultPaneRatios(viewportWidth)), [commit, viewportWidth]);
  return { commit, compact: viewportWidth < 1024, preview, ratios, reset, viewportWidth };
}
```

- [x] **Step 5: Implement the workspace and separators**

Create `web/src/features/chapter/ResizableChapterWorkspace.tsx`. Its public props are:

```tsx
type WorkspaceProps = {
  center: ReactNode;
  left: ReactNode;
  leftDrawerTitle: string;
  right: ReactNode;
  rightDrawerTitle: string;
};
```

Desktop rendering must use CSS variables and two `role="separator"` elements:

```tsx
const style: WorkspaceStyle = {
  "--workspace-left": `${ratios.left}fr`,
  "--workspace-center": `${centerRatio(ratios)}fr`,
  "--workspace-right": `${ratios.right}fr`,
};

return (
  <div className="resizable-chapter-workspace" data-testid="resizable-chapter-workspace" ref={rootRef} style={style}>
    <div className="chapter-workspace-left" data-workspace-pane="left">{left}</div>
    <WorkspaceSeparator divider="left" label="调整章节导航宽度" value={ratios.left} />
    <div className="chapter-workspace-center" data-workspace-pane="center">{center}</div>
    <WorkspaceSeparator divider="right" label="调整详情栏宽度" value={ratios.right} />
    <div className="chapter-workspace-right" data-workspace-pane="right">{right}</div>
  </div>
);
```

Implement pointer movement as `deltaPercent = (clientX - startX) / rootWidth * 100`, call `preview(moveDivider(...))` on `pointermove`, and call `commit(latestRatios)` exactly once on `pointerup`. Keyboard arrows call `moveDivider` with 1%; Shift uses 5%. Double click calls `reset`. Compact rendering must show the center plus two buttons and Ant Design left/right `Drawer` components; it must not render separators.

- [x] **Step 6: Add shared structural CSS**

Append to `web/src/app/app.css`:

```css
.resizable-chapter-workspace {
  min-width: 0;
  min-height: 0;
  height: 100%;
  display: grid;
  grid-template-columns: minmax(0, var(--workspace-left)) 8px minmax(0, var(--workspace-center)) 8px minmax(0, var(--workspace-right));
  overflow: hidden;
  background: var(--surface);
}
.chapter-workspace-left,
.chapter-workspace-center,
.chapter-workspace-right {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}
.workspace-separator {
  position: relative;
  cursor: col-resize;
  touch-action: none;
  background: transparent;
}
.workspace-separator::after {
  content: "";
  position: absolute;
  inset: 0 3px;
  background: var(--border-soft);
}
.workspace-separator:hover::after,
.workspace-separator:focus-visible::after {
  background: var(--primary);
}
.chapter-workspace-compact {
  min-height: 0;
  height: 100%;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
}
```

- [x] **Step 7: Run focused tests and build**

```bash
npm --prefix web run test -- --run src/features/chapter/workspaceLayout.test.ts src/features/chapter/ResizableChapterWorkspace.test.tsx
npm --prefix web run build
```

Expected: PASS and build succeeds.

- [x] **Step 8: Commit the shared workspace**

```bash
git add web/src/features/chapter web/src/app/app.css web/src/test/setup.ts
git commit -m "feat: add resizable chapter workspace"
```

## Task 3: Extract Shared Chapter Navigation And Compact Workflow Gate

**Files:**
- Create: `web/src/features/chapter/ChapterNavigator.tsx`
- Create: `web/src/features/chapter/ChapterNavigator.test.tsx`
- Create: `web/src/features/chapter/WorkflowGateBar.tsx`
- Create: `web/src/features/chapter/WorkflowGateBar.test.tsx`
- Modify: `web/src/features/chapter/ChapterWorkspace.tsx`
- Modify: `web/src/app/app.css`

- [x] **Step 1: Write failing navigation and gate tests**

Use `MemoryRouter` and mocked `listChapters`. Assert:

```tsx
expect(screen.getByRole("navigation", { name: "章节导航" })).toBeVisible();
fireEvent.change(screen.getByRole("textbox", { name: "搜索章节标题" }), { target: { value: "第二" } });
expect(screen.getByRole("link", { name: /第二章/ })).toHaveAttribute("href", "/projects/project-1/chapters/chapter-2");

expect(screen.getByRole("region", { name: "流程门" })).toHaveAttribute("data-expanded", "false");
fireEvent.click(screen.getByRole("button", { name: "查看原因" }));
expect(screen.getByText("未确认剧本，不允许生成分镜。")).toBeVisible();
```

- [x] **Step 2: Run tests and verify red**

```bash
npm --prefix web run test -- --run src/features/chapter/ChapterNavigator.test.tsx src/features/chapter/WorkflowGateBar.test.tsx
```

Expected: FAIL because both components are missing.

- [x] **Step 3: Implement `ChapterNavigator`**

Move the existing chapter query, search, sorting, link, state, and new-chapter markup from `SourceTab` into a component with this interface:

```tsx
type ChapterNavigatorProps = {
  chapter: ChapterRead;
  currentStateLabel?: string;
};
```

The current row uses `currentStateLabel` when supplied; other rows retain `原文已确认` or `未开始`. Preserve current routes and accessible names.

- [x] **Step 4: Implement `WorkflowGateBar` and replace `LockedReasons`**

Create:

```tsx
export function WorkflowGateBar({ details, summary }: { details: string[]; summary: string }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <section aria-label="流程门" className="workflow-gate-bar" data-expanded={expanded}>
      <InfoCircleFilled aria-hidden="true" />
      <strong>流程门</strong>
      <span>{summary}</span>
      {details.length ? (
        <Button aria-expanded={expanded} onClick={() => setExpanded((value) => !value)} size="small" type="text">
          {expanded ? "收起原因" : "查看原因"}
        </Button>
      ) : null}
      {expanded ? <ul>{details.map((detail) => <li key={detail}>{detail}</li>)}</ul> : null}
    </section>
  );
}
```

In `ChapterWorkspace`, derive one summary and a deduplicated details array from the existing gate helper functions. Render one gate for source/script tabs and delete the two full-width lock alerts.

- [x] **Step 5: Add compact gate CSS and rerun tests**

```css
.workflow-gate-bar {
  min-height: 32px;
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  color: #315d9f;
  background: #eef5ff;
  border: 1px solid #c9dcfb;
  border-radius: 5px;
}
.workflow-gate-bar ul {
  grid-column: 1 / -1;
  margin: 2px 0 4px 30px;
}
```

Run:

```bash
npm --prefix web run test -- --run src/features/chapter/ChapterNavigator.test.tsx src/features/chapter/WorkflowGateBar.test.tsx src/features/script/ScriptTab.test.tsx
```

Expected: PASS; the reason text remains covered.

- [x] **Step 6: Commit navigation and gate**

```bash
git add web/src/features/chapter web/src/features/script/ScriptTab.test.tsx web/src/app/app.css
git commit -m "refactor: share chapter navigation and workflow gate"
```

## Task 4: Move The Source View Into The Shared Full-Viewport Shell

**Files:**
- Modify: `web/src/features/chapter/SourceTab.tsx`
- Modify: `web/src/features/chapter/ChapterWorkspace.tsx`
- Modify: `web/src/features/script/ScriptTab.test.tsx`
- Modify: `web/src/app/app.css`

- [x] **Step 1: Write a failing source-workspace regression test**

Extend the existing source-tab cases in `web/src/features/script/ScriptTab.test.tsx` so the rendered source view must expose exactly one shared workspace and all three pane roles:

```tsx
expect(screen.getByTestId("resizable-chapter-workspace")).toBeInTheDocument();
expect(screen.getByRole("complementary", { name: "章节导航" })).toBeInTheDocument();
expect(screen.getByRole("region", { name: "原文编辑区" })).toBeInTheDocument();
expect(screen.getByRole("complementary", { name: "原文转剧本" })).toBeInTheDocument();
expect(screen.getByTestId("resizable-chapter-workspace").style.getPropertyValue("--workspace-center")).toBe("73fr");
```

Also assert that the chapter list occurs only once after extraction from `SourceTab`.

- [x] **Step 2: Run the focused test and verify it is red**

```bash
npm --prefix web run test -- --run src/features/script/ScriptTab.test.tsx
```

Expected: FAIL because the source view still owns fixed-width navigation and does not use `ResizableChapterWorkspace`.

- [x] **Step 3: Integrate the source content**

In `SourceTab.tsx`:

1. Delete the embedded chapter query, search, sorting, link, and new-chapter markup now owned by `ChapterNavigator`.
2. Preserve the existing source editor value, autosave behavior, model binding selector, goal, duration, validation, save-only action, and save-and-generate action.
3. Render the business content through this stable shape:

```tsx
return (
  <ResizableChapterWorkspace
    left={<ChapterNavigator chapter={chapter} currentStateLabel="原文已确认" />}
    leftDrawerTitle="章节导航"
    center={<section aria-label="原文编辑区" className="source-editor-pane">{/* existing editor */}</section>}
    right={<aside aria-label="原文转剧本" className="source-inspector-pane">{/* existing inspector */}</aside>}
    rightDrawerTitle="原文转剧本"
  />
);
```

Keep the existing `useInRouterContext` fallback so isolated component tests and non-router embeddings continue to render safely.

- [x] **Step 4: Establish the explicit full-height chain**

In `ChapterWorkspace.tsx`, add `data-editor-workspace="true"` when `activeTab` is `source` or `script`. In `app.css`, replace the source-only selector and minimum page height:

```css
.chapter-workspace[data-editor-workspace="true"] {
  height: calc(100dvh - var(--app-header-height, 52px));
  min-height: 0;
  overflow: hidden;
  display: grid;
  grid-template-rows: auto auto auto minmax(0, 1fr);
}
.chapter-workspace[data-editor-workspace="true"] .chapter-tab-content,
.chapter-workspace[data-editor-workspace="true"] .ant-tabs,
.chapter-workspace[data-editor-workspace="true"] .ant-tabs-content-holder,
.chapter-workspace[data-editor-workspace="true"] .ant-tabs-content,
.chapter-workspace[data-editor-workspace="true"] .ant-tabs-tabpane-active {
  min-height: 0;
  overflow: hidden;
}
```

Delete `.chapter-workspace:has(.source-conversion-layout)` and the fixed `height: max(864px, ...)` rule. Set source pane children to `min-width: 0; min-height: 0; overflow: auto;` and remove the old `230px / 390px` grid definition.

- [x] **Step 5: Verify source behavior and build**

```bash
npm --prefix web run test -- --run src/features/chapter/ResizableChapterWorkspace.test.tsx src/features/chapter/ChapterNavigator.test.tsx src/features/script/ScriptTab.test.tsx
npm --prefix web run build
```

Expected: PASS. Saving the source and starting mocked generation still call the same handlers.

- [x] **Step 6: Commit the source integration**

```bash
git add web/src/features/chapter/SourceTab.tsx web/src/features/chapter/ChapterWorkspace.tsx web/src/features/script/ScriptTab.test.tsx web/src/app/app.css
git commit -m "feat: use resizable workspace for source editing"
```

## Task 5: Keep Every Script State In The Same Workspace

**Files:**
- Modify: `web/src/features/script/ScriptTab.tsx`
- Modify: `web/src/features/script/ScriptTab.test.tsx`
- Modify: `web/src/app/app.css`

- [ ] **Step 1: Write failing layout-stability tests**

Add one assertion helper to `ScriptTab.test.tsx`:

```tsx
function expectSharedScriptWorkspace() {
  expect(screen.getByTestId("resizable-chapter-workspace")).toBeInTheDocument();
  expect(screen.getByRole("complementary", { name: "章节导航" })).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "剧本编辑区" })).toBeInTheDocument();
  expect(screen.getByRole("complementary", { name: "剧本详情" })).toBeInTheDocument();
}
```

Call it in existing tests for:

- waiting/empty state;
- live SSE draft;
- interrupted/failed generation with partial text;
- completed formal revision;
- revision switching and approval controls.

Assert that a transition from live to failed or completed keeps the same `resizable-chapter-workspace` DOM node and the stored ratio string unchanged.

- [ ] **Step 2: Run the focused test and verify it is red**

```bash
npm --prefix web run test -- --run src/features/script/ScriptTab.test.tsx
```

Expected: FAIL because current live, failed, and revision branches render different wrappers and widths.

- [ ] **Step 3: Normalize `ScriptTab` into pane content**

Keep all existing mutations, stream subscription, recovery, validation, revision, approval, save, reject, and retry logic. Refactor only presentation:

```tsx
return (
  <ResizableChapterWorkspace
    left={<ChapterNavigator chapter={chapter} currentStateLabel={chapterStateLabel} />}
    leftDrawerTitle="章节导航"
    center={<section aria-label="剧本编辑区" className="script-editor-workspace">{centerContent}</section>}
    right={<aside aria-label="剧本详情" className="script-inspector-pane">{rightContent}</aside>}
    rightDrawerTitle="剧本详情"
  />
);
```

Derive `centerContent` without changing state transitions:

- waiting: stable empty editor surface;
- live: incremental streamed text and current stream marker;
- failed/interrupted: retained partial text and failure marker;
- completed: selected formal revision editor.

Derive `rightContent` from data already available to the frontend:

- live/failed: run status, sequence/character count, elapsed time, stage, stable error code, retry/copy actions;
- completed: revision list, validation/QC result, save, approve, reject, and retry actions.

Do not label the current project model as the frozen run model. `ScriptGenerationRunRead` does not expose a snapshot model or target duration; show those fields only if a future typed API adds them.

- [ ] **Step 4: Remove fixed script widths and make only panes scroll**

In `app.css`:

```css
.script-editor-workspace,
.script-inspector-pane {
  min-width: 0;
  min-height: 0;
  overflow: auto;
}
.script-editor-workspace textarea {
  width: 100%;
  min-height: 100%;
  resize: none;
}
```

Remove the `.script-editor-panel` `max-width: 1080px`, `.script-live-panel` `min-height: 560px`, and state-specific fixed height rules. Replace the `autoSize` textarea prop with a height-filling textarea controlled by the center pane.

- [ ] **Step 5: Verify all script states and build**

```bash
npm --prefix web run test -- --run src/features/script/ScriptTab.test.tsx src/features/chapter/ResizableChapterWorkspace.test.tsx
npm --prefix web run build
```

Expected: PASS. Existing stream, failure retention, revision selection, and approval expectations remain green.

- [ ] **Step 6: Commit the script integration**

```bash
git add web/src/features/script/ScriptTab.tsx web/src/features/script/ScriptTab.test.tsx web/src/app/app.css
git commit -m "feat: stabilize script generation workspace"
```

## Task 6: Harden Resizing, Drawers, And Accessibility

**Files:**
- Modify: `web/src/features/chapter/ResizableChapterWorkspace.tsx`
- Modify: `web/src/features/chapter/ResizableChapterWorkspace.test.tsx`
- Modify: `web/src/features/chapter/useWorkspacePaneRatios.ts`
- Modify: `web/src/app/app.css`

- [ ] **Step 1: Add failing accessibility and compact-mode tests**

Add tests that assert:

```tsx
const leftSeparator = screen.getByRole("separator", { name: "调整章节导航宽度" });
expect(leftSeparator).toHaveAttribute("aria-orientation", "vertical");
expect(leftSeparator).toHaveAttribute("aria-valuemin", "8");
expect(leftSeparator).toHaveAttribute("aria-valuemax", "20");

fireEvent.keyDown(leftSeparator, { key: "ArrowRight", shiftKey: true });
expect(JSON.parse(localStorage.getItem(WORKSPACE_RATIO_STORAGE_KEY)!)).toMatchObject({ left: 16 });
```

At `window.innerWidth = 768`, assert separators are absent, `章节导航` and `剧本详情` toolbar buttons open one Ant Design drawer at a time, Escape closes it, and focus returns to the button that opened it.

- [ ] **Step 2: Run the tests and verify the expected red state**

```bash
npm --prefix web run test -- --run src/features/chapter/ResizableChapterWorkspace.test.tsx
```

Expected: FAIL until ARIA values, focus restoration, and compact drawer exclusivity are complete.

- [ ] **Step 3: Complete keyboard and drawer behavior**

Implement these exact rules:

- Arrow key step: `1` percentage point; Shift+Arrow: `5` percentage points.
- Left divider: ArrowLeft decreases left, ArrowRight increases left.
- Right divider: ArrowLeft increases right, ArrowRight decreases right.
- Home/End set the selected side to its legal minimum/maximum and then clamp center to 55%.
- Double click either separator restores breakpoint defaults and persists them.
- Only one compact drawer can be open; closing restores focus to its trigger.
- A resize crossing 1024px closes open drawers and reclamps the stored preference without overwriting the wide preference with `{ left: 0, right: 0 }`.

- [ ] **Step 4: Finish interaction CSS**

Add a 12px invisible pointer hit area around the 1px visual divider, clear `:focus-visible`, `cursor: col-resize`, selected-drag state, internal drawer scrolling, and:

```css
@media (prefers-reduced-motion: reduce) {
  .resizable-chapter-workspace,
  .workspace-pane-drawer .ant-drawer-content {
    transition: none;
  }
}
```

- [ ] **Step 5: Rerun focused tests and commit**

```bash
npm --prefix web run test -- --run src/features/chapter/workspaceLayout.test.ts src/features/chapter/ResizableChapterWorkspace.test.tsx
git add web/src/features/chapter/ResizableChapterWorkspace.tsx web/src/features/chapter/ResizableChapterWorkspace.test.tsx web/src/features/chapter/useWorkspacePaneRatios.ts web/src/app/app.css
git commit -m "fix: harden workspace resize accessibility"
```

## Task 7: Prove Viewport, Persistence, And Workflow Acceptance

**Files:**
- Modify: `web/tests/script-streaming.spec.ts`
- Modify: `docs/superpowers/plans/2026-07-22-resizable-script-workspace.md` (checkboxes and evidence only)

- [ ] **Step 1: Extend the local mocked E2E fixture**

Preserve the existing network mocks and add:

- two projects so global preference can be checked across project navigation;
- a long source and long streamed script so every pane has overflow;
- deterministic SSE chunks, success, failure, retry, and revision payloads;
- explicit failure for any unmatched external request.

- [ ] **Step 2: Add desktop viewport assertions**

For `1920x1080`, `1440x900`, and `1180x800`, test source, live, failed, and formal script states. Use this helper:

```ts
async function expectWorkspaceInsideViewport(page: Page) {
  const metrics = await page.evaluate(() => {
    const workspace = document.querySelector<HTMLElement>('[data-testid="resizable-chapter-workspace"]')!;
    const center = workspace.querySelector<HTMLElement>('[data-workspace-pane="center"]')!;
    const workspaceRect = workspace.getBoundingClientRect();
    const centerRect = center.getBoundingClientRect();
    return {
      bodyOverflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      bodyOverflowY: document.documentElement.scrollHeight - document.documentElement.clientHeight,
      bottom: workspaceRect.bottom,
      centerRatio: centerRect.width / workspaceRect.width,
      viewportHeight: window.innerHeight,
    };
  });
  expect(metrics.bodyOverflowX).toBeLessThanOrEqual(1);
  expect(metrics.bodyOverflowY).toBeLessThanOrEqual(1);
  expect(metrics.bottom).toBeLessThanOrEqual(metrics.viewportHeight + 1);
  expect(metrics.centerRatio).toBeGreaterThanOrEqual(0.55);
}
```

Also scroll each pane independently and assert the document scroll position remains `0`.

- [ ] **Step 3: Add drag, reset, persistence, and compact assertions**

At 1440px:

1. drag the left divider from 11% to approximately 15%;
2. reload and assert the ratio remains within `0.5` percentage point;
3. open the second project and assert the same ratio;
4. double click the divider and assert the wide default is restored.

At `768x1024`, assert no horizontal document overflow, both panes are reachable by drawer buttons, the center occupies the available width, and closing a drawer restores focus.

- [ ] **Step 4: Run the focused E2E suite**

```bash
npm --prefix web run test:e2e -- script-streaming.spec.ts
```

Expected: PASS with zero real Provider calls. Store temporary screenshots only in Playwright output; do not commit generated browser artifacts.

- [ ] **Step 5: Run the complete regression matrix**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
npm --prefix web run test:e2e
npm --prefix worker test
python3 tools/verify_m3_agnes_generation.py
python3 tools/verify_m4_chapter_rehearsal.py
python3 tools/verify_m6_supplier_model_management.py
python3 tools/verify_m6b_model_catalog_binding.py
python3 tools/verify_m6c_adapter_cutover.py
python3 tools/verify_m6d_management_ui.py
python3 migration/tools/verify_migration.py
git diff --check
```

Expected: every command exits 0. Do not run historical or current real-provider smoke tests.

- [ ] **Step 6: Perform final security and scope checks**

```bash
git diff --name-only origin/main...HEAD
git grep -nE '(sk-[A-Za-z0-9_-]{16,}|Bearer[[:space:]]+[A-Za-z0-9._-]{16,}|api[_-]?key[[:space:]]*[:=][[:space:]]*[A-Za-z0-9._-]{16,})' -- . ':!docs/superpowers/plans/2026-07-22-resizable-script-workspace.md' || true
git status --short
```

Confirm the diff contains only the files listed in this plan, no secret match is a real credential, no backend contract changed, and no generated artifact is tracked.

- [ ] **Step 7: Commit acceptance evidence**

Update only this plan's checkboxes and concise command results, then:

```bash
git add web/tests/script-streaming.spec.ts docs/superpowers/plans/2026-07-22-resizable-script-workspace.md
git commit -m "test: verify resizable script workspace"
```

## Definition Of Done

- Source, live script, failed script, and formal revision all render through the same three-pane component.
- Desktop defaults are 11/73/16 at 1440px and wider, and 14/66/20 from 1024px through 1439px.
- Side panes stay within 8–20% and 12–28%; center never drops below 55%.
- One versioned browser-local preference follows the user across tabs, chapters, and projects.
- Desktop uses internal pane scrolling with no horizontal or whole-page vertical overflow at all three required desktop viewports.
- Below 1024px, side panes become accessible drawers and preserve the wide preference.
- Pointer, keyboard, focus, reset, and reduced-motion behavior pass focused tests.
- Stream, retry, failure retention, revision, approval, and source save behavior remain unchanged.
- No backend contract, real Provider call, credential, runtime artifact, or generated private content is added.
- Full frontend, backend, Worker, migration, M3/M4/M6 verifier, and `git diff --check` commands pass.
