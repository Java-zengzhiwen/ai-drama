import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  classifyProviderStreamEvent,
  createSseParser,
  validateResponsesEventMap,
} from "./sse-parser.mjs";


test("parser joins fragmented Responses deltas", () => {
  const parser = createSseParser();
  const events = [
    ...parser.push(Buffer.from(
      'event: response.output_text.delta\ndata: {"delta":"# 第一',
    )),
    ...parser.push(Buffer.from(
      '场"}\n\nevent: response.output_text.delta\ndata: {"delta":"\\n正文"}\n\n',
    )),
    ...parser.finish(),
  ];

  assert.deepEqual(events.map(event => event.data.delta), ["# 第一场", "\n正文"]);
});


test("parser preserves a multibyte character split across network chunks", () => {
  const parser = createSseParser();
  const wire = Buffer.from(
    'event: response.output_text.delta\ndata: {"delta":"第一场"}\n\n',
    "utf8",
  );
  const splitAt = wire.indexOf(Buffer.from("一", "utf8")) + 1;
  const events = [
    ...parser.push(wire.subarray(0, splitAt)),
    ...parser.push(wire.subarray(splitAt)),
    ...parser.finish(),
  ];

  assert.equal(events[0].data.delta, "第一场");
});


test("parser ignores done and rejects an unterminated event", () => {
  const done = createSseParser();
  assert.deepEqual(done.push(Buffer.from("data: [DONE]\n\n")), []);
  assert.deepEqual(done.finish(), []);

  const malformed = createSseParser();
  malformed.push(Buffer.from('data: {"delta":"partial"}'));
  assert.throws(
    () => malformed.finish(),
    error => error.code === "PROVIDER_STREAM_MALFORMED",
  );
});


test("parser enforces the event byte limit", () => {
  const parser = createSseParser({ maxEventBytes: 8 });
  assert.throws(
    () => parser.push(Buffer.from("data: too-large")),
    error => error.code === "PROVIDER_STREAM_EVENT_TOO_LARGE",
  );
});


test("Responses event mapping emits text only for output deltas", () => {
  const eventMap = {
    delta: "response.output_text.delta",
    completed: "response.completed",
    failed: "response.failed",
  };

  assert.deepEqual(
    classifyProviderStreamEvent(
      { event: "response.output_text.delta", data: { delta: "正文" } },
      eventMap,
    ),
    { type: "text_delta", text: "正文" },
  );
  assert.equal(
    classifyProviderStreamEvent(
      { event: "response.reasoning.delta", data: { delta: "private reasoning" } },
      eventMap,
    ),
    null,
  );
  assert.deepEqual(
    classifyProviderStreamEvent(
      {
        event: "response.completed",
        data: { response: { usage: { input_tokens: 1, output_tokens: 2, total_tokens: 3 } } },
      },
      eventMap,
    ),
    { type: "usage", usage: { input_tokens: 1, output_tokens: 2, total_tokens: 3 } },
  );
  assert.deepEqual(
    classifyProviderStreamEvent(
      { event: "response.failed", data: {} },
      eventMap,
    ),
    { type: "failed", errorCode: "PROVIDER_STREAM_FAILED" },
  );
});


test("Responses event mapping cannot promote reasoning into text", () => {
  assert.equal(validateResponsesEventMap({
    delta: "response.output_text.delta",
    completed: "response.completed",
    failed: "response.failed",
  }), true);
  assert.equal(validateResponsesEventMap({
    delta: "response.reasoning.delta",
    completed: "response.completed",
    failed: "response.failed",
  }), false);
});


test("Aixora stream fixture exposes only output-text deltas", () => {
  const fixture = readFileSync(
    new URL("../../tests/fixtures/aixora/responses-stream.ndjson", import.meta.url),
    "utf8",
  ).trim().split("\n").map(line => JSON.parse(line));
  const eventMap = {
    delta: "response.output_text.delta",
    completed: "response.completed",
    failed: "response.failed",
  };

  const frames = fixture
    .map(event => classifyProviderStreamEvent(event, eventMap))
    .filter(Boolean);

  assert.deepEqual(
    frames.filter(frame => frame.type === "text_delta").map(frame => frame.text),
    ["# 第一场\n", "测试剧本正文。"],
  );
  assert.equal(JSON.stringify(frames).includes("not-visible"), false);
});
