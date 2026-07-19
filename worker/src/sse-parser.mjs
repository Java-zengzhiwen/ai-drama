import { StringDecoder } from "node:string_decoder";


function fail(code) {
  throw Object.assign(new Error(code), { code });
}


export function createSseParser({ maxEventBytes = 256 * 1024 } = {}) {
  const decoder = new StringDecoder("utf8");
  let pending = "";

  const parseAvailable = () => {
    const events = [];
    pending = pending.replaceAll("\r\n", "\n");
    for (;;) {
      const boundary = pending.indexOf("\n\n");
      if (boundary < 0) break;
      const block = pending.slice(0, boundary);
      pending = pending.slice(boundary + 2);
      if (Buffer.byteLength(block, "utf8") > maxEventBytes) {
        fail("PROVIDER_STREAM_EVENT_TOO_LARGE");
      }
      const lines = block.split("\n");
      const event = lines.find(line => line.startsWith("event:"))
        ?.slice(6).trim() || "message";
      const data = lines
        .filter(line => line.startsWith("data:"))
        .map(line => line.slice(5).trimStart())
        .join("\n");
      if (data && data !== "[DONE]") {
        try {
          events.push({ event, data: JSON.parse(data) });
        } catch {
          fail("PROVIDER_STREAM_MALFORMED");
        }
      }
    }
    if (Buffer.byteLength(pending, "utf8") > maxEventBytes) {
      fail("PROVIDER_STREAM_EVENT_TOO_LARGE");
    }
    return events;
  };

  return Object.freeze({
    push(chunk) {
      pending += decoder.write(Buffer.from(chunk));
      return parseAvailable();
    },
    finish() {
      pending += decoder.end();
      const events = parseAvailable();
      if (pending.trim()) fail("PROVIDER_STREAM_MALFORMED");
      return events;
    },
  });
}


export function classifyProviderStreamEvent(event, eventMap) {
  if (!event || !eventMap) return null;
  if (event.event === eventMap.delta) {
    return typeof event.data?.delta === "string" && event.data.delta
      ? { type: "text_delta", text: event.data.delta }
      : null;
  }
  if (event.event === eventMap.completed) {
    const raw = event.data?.response?.usage || event.data?.usage;
    if (!raw || typeof raw !== "object") return null;
    const usage = {};
    for (const key of ["input_tokens", "output_tokens", "total_tokens"]) {
      const value = Number(raw[key]);
      if (Number.isFinite(value) && value >= 0) usage[key] = value;
    }
    return { type: "usage", usage };
  }
  if (event.event === eventMap.failed) {
    return { type: "failed", errorCode: "PROVIDER_STREAM_FAILED" };
  }
  return null;
}


export function validateResponsesEventMap(eventMap) {
  return eventMap?.delta === "response.output_text.delta"
    && eventMap?.completed === "response.completed"
    && eventMap?.failed === "response.failed";
}
