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
