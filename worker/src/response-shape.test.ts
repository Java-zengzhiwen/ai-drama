import assert from "node:assert/strict";
import test from "node:test";

import { describeResponseShape, supplierErrorWithHostEvidence } from "./response-shape.mjs";


test("response shape records structure without values", () => {
  const shape = describeResponseShape({
    statusCode: 200,
    contentType: "application/json; charset=utf-8",
    byteLength: 321,
    parsed: {
      id: "private-id",
      output: [{
        type: "message",
        content: [{ type: "output_text", text: "private script" }],
      }],
      usage: { input_tokens: 10, output_tokens: 20 },
      signed_url: "https://example.test/result?signature=secret",
    },
  });

  assert.deepEqual(shape.topLevelKeys, ["id", "output", "signed_url", "usage"]);
  assert.deepEqual(shape.outputItemTypes, ["message"]);
  assert.deepEqual(shape.contentItemTypes, ["output_text"]);
  assert.equal(shape.contentType, "application/json");
  assert.equal(JSON.stringify(shape).includes("private script"), false);
  assert.equal(JSON.stringify(shape).includes("private-id"), false);
  assert.equal(JSON.stringify(shape).includes("secret"), false);
});


test("worker error keeps only host-owned response evidence", () => {
  const hostShape = { schema: "provider-response-shape-v1", topLevelKeys: ["output"] };
  const error = supplierErrorWithHostEvidence(
    {
      code: "PROVIDER_RESPONSE_MALFORMED",
      message: "private provider message",
      evidence: { leaked: "adapter-controlled" },
    },
    hostShape,
  );

  assert.deepEqual(error, {
    code: "PROVIDER_RESPONSE_MALFORMED",
    message: "PROVIDER_RESPONSE_MALFORMED",
    evidence: hostShape,
  });
  assert.equal(JSON.stringify(error).includes("adapter-controlled"), false);
  assert.equal(JSON.stringify(error).includes("private provider message"), false);
});
