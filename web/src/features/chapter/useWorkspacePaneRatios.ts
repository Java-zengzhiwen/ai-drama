import { useCallback, useEffect, useMemo, useState } from "react";
import {
  WORKSPACE_RATIO_STORAGE_KEY,
  clampPaneRatios,
  defaultPaneRatios,
  parseStoredPaneRatios,
  serializePaneRatios,
  type PaneRatios,
} from "./workspaceLayout";

const WORKSPACE_RATIO_CHANGE_EVENT = "ai-drama:workspace-pane-ratios:change";

export function useWorkspacePaneRatios() {
  const [viewportWidth, setViewportWidth] = useState(() => window.innerWidth);
  const [rawRatios, setRawRatios] = useState<PaneRatios>(() =>
    parseStoredPaneRatios(readStoredRatios())
      ?? defaultPaneRatios(window.innerWidth),
  );

  useEffect(() => {
    const updateViewport = () => setViewportWidth(window.innerWidth);
    window.addEventListener("resize", updateViewport);
    return () => window.removeEventListener("resize", updateViewport);
  }, []);

  useEffect(() => {
    const applySharedPreference = (event: Event) => {
      if (event instanceof CustomEvent) {
        const next = event.detail as PaneRatios | undefined;
        if (next && Number.isFinite(next.left) && Number.isFinite(next.right)) {
          setRawRatios(next);
        }
      }
    };
    const applyStoredPreference = (event: StorageEvent) => {
      if (event.key !== WORKSPACE_RATIO_STORAGE_KEY) return;
      setRawRatios(parseStoredPaneRatios(event.newValue) ?? defaultPaneRatios(window.innerWidth));
    };
    window.addEventListener(WORKSPACE_RATIO_CHANGE_EVENT, applySharedPreference);
    window.addEventListener("storage", applyStoredPreference);
    return () => {
      window.removeEventListener(WORKSPACE_RATIO_CHANGE_EVENT, applySharedPreference);
      window.removeEventListener("storage", applyStoredPreference);
    };
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
    window.dispatchEvent(new CustomEvent<PaneRatios>(WORKSPACE_RATIO_CHANGE_EVENT, { detail: next }));
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

function readStoredRatios() {
  try {
    return window.localStorage.getItem(WORKSPACE_RATIO_STORAGE_KEY);
  } catch {
    return null;
  }
}
