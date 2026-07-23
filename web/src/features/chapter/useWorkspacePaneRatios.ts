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
    parseStoredPaneRatios(window.localStorage.getItem(WORKSPACE_RATIO_STORAGE_KEY))
      ?? defaultPaneRatios(window.innerWidth),
  );

  useEffect(() => {
    const updateViewport = () => setViewportWidth(window.innerWidth);
    window.addEventListener("resize", updateViewport);
    return () => window.removeEventListener("resize", updateViewport);
  }, []);

  const ratios = useMemo(
    () => clampPaneRatios(rawRatios, viewportWidth),
    [rawRatios, viewportWidth],
  );

  const preview = useCallback((next: PaneRatios) => {
    setRawRatios(next);
  }, []);

  const commit = useCallback((next: PaneRatios) => {
    setRawRatios(next);
    try {
      window.localStorage.setItem(WORKSPACE_RATIO_STORAGE_KEY, serializePaneRatios(next));
    } catch {
      // Keep the workspace usable when browser storage is unavailable.
    }
  }, []);

  const reset = useCallback(() => {
    commit(defaultPaneRatios(viewportWidth));
  }, [commit, viewportWidth]);

  return {
    commit,
    compact: viewportWidth < 1024,
    preview,
    ratios,
    reset,
    viewportWidth,
  };
}
