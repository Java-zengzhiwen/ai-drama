import { describe, expect, test } from "vitest";
import { createScriptStreamState, reconcileScriptRun, reduceScriptStreamEvent } from "./streaming";

describe("script stream state", () => {
  test("appends ordered text and ignores replayed sequences", () => {
    const initial = createScriptStreamState("run-1", "prepared");
    const first = reduceScriptStreamEvent(initial, {
      sequence: 1,
      text: "# 第一场\n",
      type: "text_delta",
    });
    const replayed = reduceScriptStreamEvent(first, {
      sequence: 1,
      text: "不应重复",
      type: "text_delta",
    });
    const second = reduceScriptStreamEvent(replayed, {
      sequence: 2,
      text: "沈清荷推门入内。",
      type: "text_delta",
    });

    expect(second.text).toBe("# 第一场\n沈清荷推门入内。");
    expect(second.lastSequence).toBe(2);
    expect(second.characterCount).toBe(14);
    expect(second.status).toBe("streaming");
  });

  test("keeps partial text when generation fails", () => {
    const partial = reduceScriptStreamEvent(
      reduceScriptStreamEvent(createScriptStreamState("run-2", "prepared"), {
        sequence: 1,
        text: "# 第一场",
        type: "text_delta",
      }),
      {
        errorCode: "PROVIDER_RESPONSE_MALFORMED",
        sequence: 2,
        type: "failed",
      },
    );

    expect(partial.text).toBe("# 第一场");
    expect(partial.status).toBe("failed");
    expect(partial.errorCode).toBe("PROVIDER_RESPONSE_MALFORMED");
    expect(partial.terminal).toBe(true);
  });

  test("records the formal revision without changing streamed text", () => {
    const completed = reduceScriptStreamEvent(
      reduceScriptStreamEvent(createScriptStreamState("run-3", "prepared"), {
        sequence: 1,
        text: "完成内容",
        type: "text_delta",
      }),
      {
        revisionId: "revision-9",
        sequence: 2,
        type: "revision_completed",
      },
    );

    expect(completed.status).toBe("completed");
    expect(completed.revisionId).toBe("revision-9");
    expect(completed.text).toBe("完成内容");
    expect(completed.terminal).toBe(true);
  });

  test("tracks finalization and validation stages", () => {
    const finalizing = reduceScriptStreamEvent(
      createScriptStreamState("run-stage", "streaming"),
      { sequence: 1, stage: "finalizing", type: "stage" },
    );
    const validating = reduceScriptStreamEvent(
      finalizing,
      { sequence: 2, stage: "validating", type: "stage" },
    );

    expect(finalizing.status).toBe("finalizing");
    expect(validating.stage).toBe("validating");
  });

  test("does not skip missing text when status polling is ahead of the browser", () => {
    const received = reduceScriptStreamEvent(createScriptStreamState("run-4", "prepared"), {
      sequence: 1,
      text: "已收到",
      type: "text_delta",
    });

    const reconciled = reconcileScriptRun(received, {
      run_id: "run-4",
      status: "streaming",
      last_sequence: 5,
      character_count: 20,
      revision_id: "",
      error_code: "",
    });

    expect(reconciled.lastSequence).toBe(1);
    expect(reconciled.characterCount).toBe(3);
    expect(reconciled.text).toBe("已收到");
    expect(reconciled.reconnecting).toBe(true);
  });
});
