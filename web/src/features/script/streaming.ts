import type { ScriptGenerationRunRead, ScriptGenerationStatus } from "./api";

export type ScriptStreamState = {
  active: boolean;
  characterCount: number;
  errorCode: string;
  lastSequence: number;
  reconnecting: boolean;
  revisionId: string;
  runId: string;
  startedAt: number;
  status: ScriptGenerationStatus;
  terminal: boolean;
  text: string;
};

export type ScriptStreamEvent =
  | { sequence: number; text: string; type: "text_delta" }
  | { sequence: number; type: "usage"; usage?: Record<string, unknown> }
  | { errorCode: string; sequence: number; type: "failed" }
  | { revisionId: string; sequence: number; type: "revision_completed" };

const terminalStatuses = new Set<ScriptGenerationStatus>([
  "completed",
  "failed",
  "unknown_outcome",
]);

export function createScriptStreamState(
  runId: string,
  status: ScriptGenerationStatus,
  initial?: Partial<Pick<ScriptGenerationRunRead, "character_count" | "error_code" | "last_sequence" | "revision_id">>,
): ScriptStreamState {
  return {
    active: Boolean(runId),
    characterCount: initial?.character_count ?? 0,
    errorCode: initial?.error_code ?? "",
    lastSequence: initial?.last_sequence ?? 0,
    reconnecting: false,
    revisionId: initial?.revision_id ?? "",
    runId,
    startedAt: Date.now(),
    status,
    terminal: terminalStatuses.has(status),
    text: "",
  };
}

export function reduceScriptStreamEvent(
  state: ScriptStreamState,
  event: ScriptStreamEvent,
): ScriptStreamState {
  if (event.sequence <= state.lastSequence) {
    return state;
  }
  if (event.type === "text_delta") {
    const text = `${state.text}${event.text}`;
    return {
      ...state,
      characterCount: text.length,
      lastSequence: event.sequence,
      reconnecting: false,
      status: "streaming",
      text,
    };
  }
  if (event.type === "failed") {
    return {
      ...state,
      errorCode: event.errorCode,
      lastSequence: event.sequence,
      reconnecting: false,
      status: "failed",
      terminal: true,
    };
  }
  if (event.type === "revision_completed") {
    return {
      ...state,
      lastSequence: event.sequence,
      reconnecting: false,
      revisionId: event.revisionId,
      status: "completed",
      terminal: true,
    };
  }
  return {
    ...state,
    lastSequence: event.sequence,
    reconnecting: false,
  };
}

export function reconcileScriptRun(
  state: ScriptStreamState,
  run: ScriptGenerationRunRead,
): ScriptStreamState {
  return {
    ...state,
    characterCount: Math.max(state.characterCount, run.character_count),
    errorCode: run.error_code || state.errorCode,
    lastSequence: Math.max(state.lastSequence, run.last_sequence),
    reconnecting: !terminalStatuses.has(run.status),
    revisionId: run.revision_id || state.revisionId,
    status: run.status,
    terminal: terminalStatuses.has(run.status),
  };
}

