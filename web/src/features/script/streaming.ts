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
  stage: "" | "finalizing" | "validating";
  status: ScriptGenerationStatus;
  terminal: boolean;
  text: string;
};

export type ScriptStreamEvent =
  | { sequence: number; stage: "finalizing" | "validating"; type: "stage" }
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
    characterCount: 0,
    errorCode: initial?.error_code ?? "",
    lastSequence: 0,
    reconnecting: false,
    revisionId: initial?.revision_id ?? "",
    runId,
    startedAt: Date.now(),
    stage: status === "finalizing" ? "finalizing" : "",
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
  if (event.type === "stage") {
    return {
      ...state,
      lastSequence: event.sequence,
      reconnecting: false,
      stage: event.stage,
      status: "finalizing",
    };
  }
  return {
    ...state,
    lastSequence: event.sequence,
    reconnecting: false,
  };
}

const storagePrefix = "ai-drama:script-generation:";

export function persistActiveScriptRun(chapterId: string, run: ScriptGenerationRunRead) {
  try {
    sessionStorage.setItem(`${storagePrefix}${chapterId}`, JSON.stringify(run));
  } catch {
    // The durable server-side session remains authoritative when storage is unavailable.
  }
}

export function loadActiveScriptRun(chapterId: string): ScriptGenerationRunRead | null {
  try {
    const raw = sessionStorage.getItem(`${storagePrefix}${chapterId}`);
    if (!raw) return null;
    const value = JSON.parse(raw) as ScriptGenerationRunRead;
    return typeof value?.run_id === "string" && value.run_id ? value : null;
  } catch {
    return null;
  }
}

export function clearActiveScriptRun(chapterId: string) {
  try {
    sessionStorage.removeItem(`${storagePrefix}${chapterId}`);
  } catch {
    // Nothing else is required; the server-side run remains auditable.
  }
}

export function reconcileScriptRun(
  state: ScriptStreamState,
  run: ScriptGenerationRunRead,
): ScriptStreamState {
  return {
    ...state,
    characterCount: state.characterCount,
    errorCode: run.error_code || state.errorCode,
    lastSequence: state.lastSequence,
    reconnecting: !terminalStatuses.has(run.status),
    revisionId: run.revision_id || state.revisionId,
    status: run.status,
    terminal: terminalStatuses.has(run.status),
  };
}
