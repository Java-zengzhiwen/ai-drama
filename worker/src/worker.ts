import vm from "node:vm";
import dns from "node:dns";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import https from "node:https";
import net from "node:net";
import { createPinnedLookup } from "./pinned-lookup.mjs";
import { assertNotRedirect, assertPeerAddress, isPublicAddress } from "./network-policy.mjs";
import { describeResponseShape, supplierErrorWithHostEvidence } from "./response-shape.mjs";
import {
  classifyProviderStreamEvent,
  createSseParser,
  validateResponsesEventMap,
} from "./sse-parser.mjs";
import {
  assertInputBudget,
  authorizeDeclaredInputReference,
  authorizeProviderResultDownload,
  buildMultipartBody,
  collectProviderResultUrls,
  decodeBase64,
  decodeDeclaredImageReference,
  providerHttpErrorCode,
  validateImageBuffer,
  validateOperationMediaBuffer,
} from "./media-helpers.mjs";


function respond(payload) {
  const output = JSON.stringify(payload);
  const limit = Number(request?.maxOutputBytes || 4 * 1024 * 1024);
  if (Buffer.byteLength(output, "utf8") > limit) {
    process.stdout.write(JSON.stringify({
      ok: false,
      error: {
        code: "SUPPLIER_WORKER_OUTPUT_TOO_LARGE",
        message: "supplier worker output too large",
      },
    }));
    return;
  }
  process.stdout.write(output);
}


let request;
let streamSequence = 0;
let streamOutputBytes = 0;
function respondStreamFrame(payload) {
  const frame = { ...payload, sequence: streamSequence++ };
  const output = `${JSON.stringify(frame)}\n`;
  streamOutputBytes += Buffer.byteLength(output, "utf8");
  if (streamOutputBytes > Number(request?.maxOutputBytes || 4 * 1024 * 1024)) {
    const error = new Error("SUPPLIER_WORKER_OUTPUT_TOO_LARGE");
    error.code = "SUPPLIER_WORKER_OUTPUT_TOO_LARGE";
    throw error;
  }
  process.stdout.write(output);
}


try {
  const input = await new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", chunk => data += chunk);
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  });
  request = JSON.parse(input);
} catch {
  process.stdout.write(JSON.stringify({
    ok: false,
    error: { code: "SUPPLIER_WORKER_PROTOCOL_ERROR", message: "invalid worker request" },
  }));
  process.exit(0);
}

const streamingInvocation = request.workerProtocolVersion === "2"
  && request.helperApiVersion === "ai-drama-helper-v3"
  && request.operation === "textStream";
if (!new Set(["1", "2"]).has(request.workerProtocolVersion)) {
  respond({ ok: false, error: { code: "SUPPLIER_WORKER_PROTOCOL_ERROR", message: "unsupported worker protocol" } });
  process.exit(0);
}
if (
  !(request.workerProtocolVersion === "1"
    && new Set(["ai-drama-helper-v1", "ai-drama-helper-v2"]).has(request.helperApiVersion))
  && !(request.workerProtocolVersion === "2" && request.helperApiVersion === "ai-drama-helper-v3")
  || request.workerRuntimeVersion !== process.version
) {
  if (request.workerProtocolVersion === "2") {
    respondStreamFrame({ type: "failed", errorCode: "SUPPLIER_RUNTIME_UNAVAILABLE", evidence: {} });
  } else {
    respond({
      ok: false,
      error: {
        code: "SUPPLIER_RUNTIME_UNAVAILABLE",
        message: "supplier runtime fingerprint is unavailable",
      },
    });
  }
  process.exit(0);
}

const networkError = request.mode === "validation"
  ? "NETWORK_DISABLED_DURING_VALIDATION"
  : "NETWORK_HELPER_UNAVAILABLE";
let lastProviderResponseShape = null;
let lastProviderStreamEvidence = null;
const configUrls = [];
const collectConfigUrls = value => {
  if (typeof value === "string" && /^https:\/\//.test(value)) configUrls.push(value);
  else if (Array.isArray(value)) value.forEach(collectConfigUrls);
  else if (value && typeof value === "object") Object.values(value).forEach(collectConfigUrls);
};
collectConfigUrls(request.payload?.config || {});
const allowedOrigins = new Set(configUrls.map(value => new URL(value).origin));
async function resolvePublic(hostname) {
  if (hostname.startsWith("[") && hostname.endsWith("]")) hostname = hostname.slice(1, -1);
  const literal = net.isIP(hostname);
  const records = literal
    ? [{ address: hostname, family: literal }]
    : await dns.promises.lookup(hostname, { all: true, verbatim: true });
  if (!records.length || records.some(record => !isPublicAddress(record.address))) {
    const error = new Error("HTTP_DESTINATION_NOT_ALLOWED");
    error.code = "HTTP_DESTINATION_NOT_ALLOWED";
    throw error;
  }
  return records;
}

function httpsRequest(url, options, records, requestBody = undefined, byteLimit = undefined) {
  return new Promise((resolve, reject) => {
    const allowedAddresses = new Set(records.map(record => record.address));
    const lookup = createPinnedLookup(records);
    const requestHandle = https.request(url, {
      method: String(options?.method || "GET"),
      headers: options?.headers || {},
      timeout: Math.max(1, Number(request.timeoutMs)),
      servername: url.hostname,
      lookup,
    }, response => {
      try {
        assertNotRedirect(response.statusCode);
      } catch (error) {
        response.resume();
        reject(error);
        return;
      }
      const chunks = [];
      let size = 0;
      const limit = byteLimit === undefined
        ? (options?.responseType === "bytes"
          ? Number(request.maxMediaBytes || 512 * 1024 * 1024)
          : Number(request.maxOutputBytes || 4 * 1024 * 1024))
        : Number(byteLimit);
      response.on("data", chunk => {
        size += chunk.length;
        if (size > limit) response.destroy(Object.assign(new Error("SUPPLIER_WORKER_OUTPUT_TOO_LARGE"), { code: "SUPPLIER_WORKER_OUTPUT_TOO_LARGE" }));
        else chunks.push(chunk);
      });
      response.on("end", () => resolve({ response, buffer: Buffer.concat(chunks) }));
      response.on("error", reject);
    });
    requestHandle.on("socket", socket => {
      socket.once("secureConnect", () => {
        try { assertPeerAddress(socket.remoteAddress, allowedAddresses); }
        catch (error) { requestHandle.destroy(error); }
      });
    });
    requestHandle.on("timeout", () => requestHandle.destroy(Object.assign(new Error("SUPPLIER_WORKER_TIMEOUT"), { code: "SUPPLIER_WORKER_TIMEOUT" })));
    requestHandle.on("error", reject);
    if (requestBody !== undefined) requestHandle.write(requestBody);
    else if (options?.body !== undefined) requestHandle.write(JSON.stringify(options.body));
    requestHandle.end();
  });
}

async function writeMediaReference(buffer, mediaType) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "ai-drama-worker-media-"));
  const localFile = path.join(directory, "result.bin");
  await fs.writeFile(localFile, buffer, { mode: 0o600 });
  return {
    local_file: localFile,
    sha256: crypto.createHash("sha256").update(buffer).digest("hex"),
    size: buffer.length,
    media_type: mediaType,
  };
}

const declaredInputReferences = new Set(
  (Array.isArray(request.payload?.request?.input_images)
    ? request.payload.request.input_images
    : [])
    .filter(value => typeof value === "string"),
);
const providerResultUrls = new Set();

async function downloadDeclaredInput(value, maxFileBytes) {
  const raw = authorizeDeclaredInputReference(value, declaredInputReferences);
  if (raw.startsWith("data:")) {
    return decodeDeclaredImageReference(
      raw,
      maxFileBytes,
    );
  }
  const url = new URL(raw);
  if (url.protocol !== "https:" || url.port && url.port !== "443") {
    const error = new Error("HTTP_DESTINATION_NOT_ALLOWED");
    error.code = "HTTP_DESTINATION_NOT_ALLOWED";
    throw error;
  }
  const records = await resolvePublic(url.hostname);
  const { response, buffer } = await httpsRequest(
    url,
    { method: "GET", responseType: "bytes" },
    records,
    undefined,
    maxFileBytes,
  );
  if (response.statusCode < 200 || response.statusCode >= 300) {
    const code = providerHttpErrorCode(response.statusCode);
    const error = new Error(code);
    error.code = code;
    throw error;
  }
  const mediaType = String(response.headers["content-type"] || "").split(";", 1)[0].toLowerCase();
  if (!/^image\/(?:png|jpeg|webp)$/.test(mediaType)) {
    const error = new Error("SUPPLIER_INPUT_MEDIA_INVALID");
    error.code = "SUPPLIER_INPUT_MEDIA_INVALID";
    throw error;
  }
  validateImageBuffer(buffer, mediaType);
  return { buffer, mediaType };
}

const hostHttpStream = async options => {
  if (request.mode === "validation") {
    const error = new Error("NETWORK_DISABLED_DURING_VALIDATION");
    error.code = "NETWORK_DISABLED_DURING_VALIDATION";
    throw error;
  }
  if (!streamingInvocation || allowedOrigins.size === 0) {
    const error = new Error("NETWORK_HELPER_UNAVAILABLE");
    error.code = "NETWORK_HELPER_UNAVAILABLE";
    throw error;
  }
  const rawUrl = String(options?.url || "");
  const url = new URL(rawUrl);
  if (
    url.protocol !== "https:"
    || url.port && url.port !== "443"
    || !allowedOrigins.has(url.origin)
  ) {
    const error = new Error("HTTP_DESTINATION_NOT_ALLOWED");
    error.code = "HTTP_DESTINATION_NOT_ALLOWED";
    throw error;
  }
  for (const [key, value] of Object.entries(options?.query || {})) {
    url.searchParams.set(key, String(value));
  }
  const eventMap = options?.eventMap || {};
  if (!validateResponsesEventMap(eventMap)) {
    const error = new Error("PROVIDER_STREAM_CONTRACT_INVALID");
    error.code = "PROVIDER_STREAM_CONTRACT_INVALID";
    throw error;
  }
  const records = await resolvePublic(url.hostname);
  const requestBody = options?.body === undefined
    ? undefined
    : JSON.stringify(options.body);
  const allowedAddresses = new Set(records.map(record => record.address));
  const lookup = createPinnedLookup(records);
  const parser = createSseParser();
  const eventTypes = new Set();
  let eventCount = 0;
  let byteLength = 0;
  let httpStatus = 0;
  let contentType = "";
  let sawCompleted = false;
  const updateEvidence = () => {
    lastProviderStreamEvidence = Object.freeze({
      schema: "provider-stream-shape-v1",
      httpStatus,
      contentType,
      byteLength,
      eventCount,
      eventTypes: [...eventTypes].sort(),
    });
  };
  const handleEvent = event => {
    eventCount += 1;
    eventTypes.add(String(event.event || "message"));
    if (event.event === eventMap.completed) sawCompleted = true;
    updateEvidence();
    const mapped = classifyProviderStreamEvent(event, eventMap);
    if (!mapped) return;
    if (mapped.type === "failed") {
      const error = new Error(mapped.errorCode);
      error.code = mapped.errorCode;
      throw error;
    }
    respondStreamFrame(mapped);
  };

  return new Promise((resolve, reject) => {
    let settled = false;
    const finishError = error => {
      if (settled) return;
      settled = true;
      reject(error);
    };
    const requestHandle = https.request(url, {
      method: String(options?.method || "GET"),
      headers: options?.headers || {},
      timeout: Math.max(1, Number(request.timeoutMs)),
      servername: url.hostname,
      lookup,
    }, response => {
      try {
        assertNotRedirect(response.statusCode);
        if (response.statusCode < 200 || response.statusCode >= 300) {
          const code = providerHttpErrorCode(response.statusCode);
          throw Object.assign(new Error(code), { code });
        }
        httpStatus = Number(response.statusCode || 0);
        contentType = String(response.headers["content-type"] || "")
          .split(";", 1)[0].toLowerCase();
        if (contentType !== "text/event-stream") {
          throw Object.assign(
            new Error("PROVIDER_STREAM_MALFORMED"),
            { code: "PROVIDER_STREAM_MALFORMED" },
          );
        }
        updateEvidence();
        respondStreamFrame({ type: "started" });
      } catch (error) {
        response.resume();
        finishError(error);
        return;
      }
      response.on("data", chunk => {
        if (settled) return;
        try {
          byteLength += chunk.length;
          if (byteLength > Number(request.maxOutputBytes || 4 * 1024 * 1024)) {
            throw Object.assign(
              new Error("SUPPLIER_WORKER_OUTPUT_TOO_LARGE"),
              { code: "SUPPLIER_WORKER_OUTPUT_TOO_LARGE" },
            );
          }
          updateEvidence();
          for (const event of parser.push(chunk)) handleEvent(event);
        } catch (error) {
          response.destroy(error);
          finishError(error);
        }
      });
      response.on("end", () => {
        if (settled) return;
        try {
          for (const event of parser.finish()) handleEvent(event);
          if (!sawCompleted) {
            throw Object.assign(
              new Error("PROVIDER_STREAM_MALFORMED"),
              { code: "PROVIDER_STREAM_MALFORMED" },
            );
          }
          settled = true;
          updateEvidence();
          resolve({ evidence: lastProviderStreamEvidence });
        } catch (error) {
          finishError(error);
        }
      });
      response.on("error", finishError);
    });
    requestHandle.on("socket", socket => {
      socket.once("secureConnect", () => {
        try { assertPeerAddress(socket.remoteAddress, allowedAddresses); }
        catch (error) { requestHandle.destroy(error); }
      });
    });
    requestHandle.on("timeout", () => requestHandle.destroy(
      Object.assign(new Error("SUPPLIER_WORKER_TIMEOUT"), { code: "SUPPLIER_WORKER_TIMEOUT" }),
    ));
    requestHandle.on("error", finishError);
    if (requestBody !== undefined) requestHandle.write(requestBody);
    requestHandle.end();
  });
};

const hostHttpRequest = async options => {
  if (request.mode === "validation") {
    const error = new Error("NETWORK_DISABLED_DURING_VALIDATION");
    error.code = "NETWORK_DISABLED_DURING_VALIDATION";
    throw error;
  }
  if (allowedOrigins.size === 0) {
    const error = new Error("NETWORK_HELPER_UNAVAILABLE");
    error.code = "NETWORK_HELPER_UNAVAILABLE";
    throw error;
  }
  const rawUrl = String(options?.url || "");
  const url = new URL(rawUrl);
  const providerResultDownload = providerResultUrls.has(rawUrl);
  if (providerResultDownload) authorizeProviderResultDownload(options, providerResultUrls);
  if (
    url.protocol !== "https:"
    || url.port && url.port !== "443"
    || (!allowedOrigins.has(url.origin) && !providerResultDownload)
  ) {
    const error = new Error("HTTP_DESTINATION_NOT_ALLOWED");
    error.code = "HTTP_DESTINATION_NOT_ALLOWED";
    throw error;
  }
  for (const [key, value] of Object.entries(options?.query || {})) {
    url.searchParams.set(key, String(value));
  }
  let requestBody;
  let requestOptions = options;
  if (options?.multipart) {
    if (!new Set(["ai-drama-helper-v2", "ai-drama-helper-v3"])
      .has(request.helperApiVersion)) {
      const error = new Error("SUPPLIER_RUNTIME_UNAVAILABLE");
      error.code = "SUPPLIER_RUNTIME_UNAVAILABLE";
      throw error;
    }
    const files = Array.isArray(options.multipart.files) ? options.multipart.files : [];
    if (files.length === 0 || files.length > 16) {
      const error = new Error("SUPPLIER_MULTIPART_INVALID");
      error.code = "SUPPLIER_MULTIPART_INVALID";
      throw error;
    }
    const resolvedFiles = [];
    const aggregateLimit = Math.min(
      Number(request.maxMediaBytes || 512 * 1024 * 1024),
      64 * 1024 * 1024,
    );
    const perFileLimit = Math.min(aggregateLimit, 25 * 1024 * 1024);
    let inputBytes = 0;
    for (const [index, file] of files.entries()) {
      const downloaded = await downloadDeclaredInput(
        file?.url,
        Math.min(perFileLimit, aggregateLimit - inputBytes),
      );
      inputBytes = assertInputBudget(inputBytes, downloaded.buffer.length, aggregateLimit);
      resolvedFiles.push({
        fieldName: String(file?.fieldName || "image[]"),
        filename: `image-${index + 1}.${downloaded.mediaType === "image/jpeg" ? "jpg" : downloaded.mediaType.slice(6)}`,
        mediaType: downloaded.mediaType,
        data: downloaded.buffer,
      });
    }
    const boundary = `ai-drama-${crypto.randomBytes(18).toString("hex")}`;
    requestBody = buildMultipartBody(
      { fields: options.multipart.fields || {}, files: resolvedFiles },
      boundary,
      aggregateLimit,
    );
    requestOptions = {
      ...options,
      body: undefined,
      headers: {
        ...(options.headers || {}),
        "Content-Type": `multipart/form-data; boundary=${boundary}`,
        "Content-Length": String(requestBody.length),
      },
    };
  }
  const records = await resolvePublic(url.hostname);
  const { response, buffer } = await httpsRequest(url, requestOptions, records, requestBody);
  if (response.statusCode < 200 || response.statusCode >= 300) {
    const code = providerHttpErrorCode(response.statusCode);
    const error = new Error(code);
    error.code = code;
    throw error;
  }
  if (options?.responseType === "bytes") {
    const mediaType = String(response.headers["content-type"] || "").split(";", 1)[0].toLowerCase();
    validateOperationMediaBuffer(buffer, mediaType, String(request.operation));
    return writeMediaReference(
      buffer,
      mediaType || "application/octet-stream",
    );
  }
  try {
    const parsed = JSON.parse(buffer.toString("utf8"));
    lastProviderResponseShape = describeResponseShape({
      statusCode: response.statusCode,
      contentType: response.headers["content-type"],
      byteLength: buffer.length,
      parsed,
    });
    for (const value of collectProviderResultUrls(parsed)) providerResultUrls.add(value);
    return parsed;
  }
  catch {
    const error = new Error("PROVIDER_RESPONSE_MALFORMED");
    error.code = "PROVIDER_RESPONSE_MALFORMED";
    throw error;
  }
};
const hostMediaRequest = async options => {
  if (options?.operation !== "decodeBase64") {
    const error = new Error("SUPPLIER_MEDIA_OPERATION_INVALID");
    error.code = "SUPPLIER_MEDIA_OPERATION_INVALID";
    throw error;
  }
  const mediaType = String(options.mediaType || "").toLowerCase();
  if (!/^image\/(?:png|jpeg|webp)$/.test(mediaType)) {
    const error = new Error("SUPPLIER_INPUT_MEDIA_INVALID");
    error.code = "SUPPLIER_INPUT_MEDIA_INVALID";
    throw error;
  }
  const buffer = decodeBase64(
    options.value,
    mediaType,
    Number(request.maxMediaBytes || 512 * 1024 * 1024),
  );
  return writeMediaReference(buffer, mediaType);
};
const context = vm.createContext(
  {
    payloadJson: JSON.stringify(request.payload),
    operationName: String(request.operation),
    networkErrorCode: networkError,
    executionMode: request.mode === "execution",
    helperV2: new Set(["ai-drama-helper-v2", "ai-drama-helper-v3"])
      .has(request.helperApiVersion),
    helperV3: request.helperApiVersion === "ai-drama-helper-v3",
  },
  { codeGeneration: { strings: false, wasm: false } },
);

try {
  new vm.Script(`
    globalThis.module = { exports: {} };
    globalThis.exports = globalThis.module.exports;
    globalThis.payload = JSON.parse(payloadJson);
    globalThis.operation = operationName;
    globalThis.__httpQueue = [];
    globalThis.__httpStreamQueue = [];
    globalThis.__mediaQueue = [];
    const denyNetwork = async () => {
      const error = new Error(networkErrorCode);
      error.code = networkErrorCode;
      throw error;
    };
    const queueNetwork = options => new Promise((resolve, reject) => {
      globalThis.__httpQueue.push({ options, resolve, reject });
    });
    const queueStream = options => new Promise((resolve, reject) => {
      globalThis.__httpStreamQueue.push({ options, resolve, reject });
    });
    const queueMedia = options => new Promise((resolve, reject) => {
      globalThis.__mediaQueue.push({ options, resolve, reject });
    });
    const helperValues = {
      http: Object.freeze({
        request: executionMode ? queueNetwork : denyNetwork,
        ...(helperV3 ? { stream: executionMode ? queueStream : denyNetwork } : {}),
      }),
      log: Object.freeze({ info: () => undefined, warning: () => undefined }),
    };
    if (helperV2) helperValues.media = Object.freeze({
        decodeBase64: executionMode
          ? (value, mediaType) => queueMedia({ operation: "decodeBase64", value, mediaType })
          : denyNetwork,
    });
    globalThis.helpers = Object.freeze(helperValues);
  `, { filename: "supplier-bootstrap.cjs" }).runInContext(
    context,
    { timeout: request.timeoutMs },
  );
  new vm.Script(request.compiledCode, { filename: "supplier.cjs" }).runInContext(
    context,
    { timeout: request.timeoutMs },
  );
  new vm.Script(
    "globalThis.__supplierResult = Promise.resolve(module.exports[operation](payload, helpers));",
    { filename: "supplier-invoke.cjs" },
  ).runInContext(context, { timeout: request.timeoutMs });
  let settled = false;
  let value;
  let supplierError;
  context.__supplierResult.then(
    result => { settled = true; value = result; },
    error => { settled = true; supplierError = error; },
  );
  const deadline = Date.now() + Number(request.timeoutMs);
  while (!settled) {
    const pending = context.__httpQueue.shift();
    if (pending) {
      try { pending.resolve(await hostHttpRequest(pending.options)); }
      catch (error) { pending.reject({ code: error?.code || "SUPPLIER_EXECUTION_FAILED" }); }
    } else {
      const pendingStream = context.__httpStreamQueue.shift();
      if (pendingStream) {
        try { pendingStream.resolve(await hostHttpStream(pendingStream.options)); }
        catch (error) { pendingStream.reject({ code: error?.code || "SUPPLIER_EXECUTION_FAILED" }); }
        continue;
      }
      const pendingMedia = context.__mediaQueue.shift();
      if (pendingMedia) {
        try { pendingMedia.resolve(await hostMediaRequest(pendingMedia.options)); }
        catch (error) { pendingMedia.reject({ code: error?.code || "SUPPLIER_EXECUTION_FAILED" }); }
        continue;
      }
      if (Date.now() >= deadline) {
        const error = new Error("SUPPLIER_WORKER_TIMEOUT");
        error.code = "SUPPLIER_WORKER_TIMEOUT";
        throw error;
      }
      await new Promise(resolve => setImmediate(resolve));
    }
  }
  if (supplierError) throw supplierError;
  if (streamingInvocation) {
    respondStreamFrame({ type: "completed", evidence: value?.evidence || {} });
  } else {
    respond({
      ok: true,
      workerProtocolVersion: request.workerProtocolVersion,
      helperApiVersion: request.helperApiVersion,
      workerRuntimeVersion: process.version,
      value,
    });
  }
} catch (error) {
  if (streamingInvocation) {
    respondStreamFrame({
      type: "failed",
      errorCode: error?.code || "SUPPLIER_EXECUTION_FAILED",
      evidence: lastProviderStreamEvidence || {},
    });
  } else {
    respond({
      ok: false,
      error: supplierErrorWithHostEvidence(error, lastProviderResponseShape),
    });
  }
}
