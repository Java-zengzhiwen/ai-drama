import { describe, expect, test } from "vitest";
import { createScriptStreamState, reduceScriptStreamEvent } from "./streaming";

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
});
