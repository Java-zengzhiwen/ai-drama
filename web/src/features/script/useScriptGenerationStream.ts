import { useCallback, useEffect, useState } from "react";
import { getScriptGenerationRun, type ScriptGenerationRunRead } from "./api";
import {
  createScriptStreamState,
  reconcileScriptRun,
  reduceScriptStreamEvent,
  type ScriptStreamEvent,
  type ScriptStreamState,
} from "./streaming";

const emptyState = createScriptStreamState("", "prepared");

export function useScriptGenerationStream(run: ScriptGenerationRunRead | null) {
  const [state, setState] = useState<ScriptStreamState>(emptyState);

  useEffect(() => {
    if (!run?.run_id) {
      setState(emptyState);
      return;
    }

    let disposed = false;
    const source = new EventSource(
      `/api/script-generation-runs/${encodeURIComponent(run.run_id)}/events?after_sequence=0`,
    );
    setState(createScriptStreamState(run.run_id, run.status, run));

    const accept = (type: ScriptStreamEvent["type"]) => (rawEvent: Event) => {
      if (disposed) {
        return;
      }
      const payload = JSON.parse((rawEvent as MessageEvent<string>).data) as Record<string, unknown>;
      const sequence = Number(payload.sequence ?? 0);
      let event: ScriptStreamEvent;
      if (type === "stage") {
        const rawStage = String(payload.status ?? "");
        if (rawStage !== "finalizing" && rawStage !== "validating") return;
        event = { sequence, stage: rawStage, type };
      } else if (type === "text_delta") {
        event = { sequence, text: String(payload.text ?? ""), type };
      } else if (type === "failed") {
        event = { errorCode: String(payload.error_code ?? "SUPPLIER_EXECUTION_FAILED"), sequence, type };
      } else if (type === "revision_completed") {
        event = { revisionId: String(payload.revision_id ?? ""), sequence, type };
      } else {
        event = { sequence, type, usage: payload.usage as Record<string, unknown> | undefined };
      }
      setState((current) => reduceScriptStreamEvent(current, event));
      if (type === "failed" || type === "revision_completed") {
        source.close();
      }
    };

    const textHandler = accept("text_delta");
    const stageHandler = accept("stage");
    const usageHandler = accept("usage");
    const failedHandler = accept("failed");
    const completedHandler = accept("revision_completed");
    source.addEventListener("stage", stageHandler);
    source.addEventListener("text_delta", textHandler);
    source.addEventListener("usage", usageHandler);
    source.addEventListener("failed", failedHandler);
    source.addEventListener("revision_completed", completedHandler);
    source.onopen = () => {
      if (!disposed) {
        setState((current) => ({ ...current, reconnecting: false }));
      }
    };
    source.onerror = () => {
      if (disposed) {
        return;
      }
      setState((current) => ({ ...current, reconnecting: true }));
      void getScriptGenerationRun(run.run_id)
        .then((latest) => {
          if (!disposed) {
            setState((current) => reconcileScriptRun(current, latest));
            if (["completed", "failed", "unknown_outcome"].includes(latest.status)) {
              source.close();
            }
          }
        })
        .catch(() => undefined);
    };

    return () => {
      disposed = true;
      source.close();
    };
  }, [run]);

  const clear = useCallback(() => setState(emptyState), []);
  return { ...state, clear };
}
