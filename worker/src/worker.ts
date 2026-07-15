import vm from "node:vm";
import dns from "node:dns";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import https from "node:https";
import net from "node:net";
import { createPinnedLookup } from "./pinned-lookup.mjs";
import { buildMultipartBody, decodeBase64 } from "./media-helpers.mjs";


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

if (request.workerProtocolVersion !== "1") {
  respond({
    ok: false,
    error: { code: "SUPPLIER_WORKER_PROTOCOL_ERROR", message: "unsupported worker protocol" },
  });
  process.exit(0);
}
if (
  request.helperApiVersion !== "ai-drama-helper-v1"
  || request.workerRuntimeVersion !== process.version
) {
  respond({
    ok: false,
    error: {
      code: "SUPPLIER_RUNTIME_UNAVAILABLE",
      message: "supplier runtime fingerprint is unavailable",
    },
  });
  process.exit(0);
}

const networkError = request.mode === "validation"
  ? "NETWORK_DISABLED_DURING_VALIDATION"
  : "NETWORK_HELPER_UNAVAILABLE";
const configUrls = [];
const collectConfigUrls = value => {
  if (typeof value === "string" && /^https:\/\//.test(value)) configUrls.push(value);
  else if (Array.isArray(value)) value.forEach(collectConfigUrls);
  else if (value && typeof value === "object") Object.values(value).forEach(collectConfigUrls);
};
collectConfigUrls(request.payload?.config || {});
const allowedOrigins = new Set(configUrls.map(value => new URL(value).origin));
function isPublicAddress(address) {
  if (net.isIP(address) === 4) {
    const octets = address.split(".").map(Number);
    const [a, b] = octets;
    return !(
      a === 0 || a === 10 || a === 127 || a >= 224
      || (a === 100 && b >= 64 && b <= 127)
      || (a === 169 && b === 254)
      || (a === 172 && b >= 16 && b <= 31)
      || (a === 192 && b === 168)
      || (a === 198 && (b === 18 || b === 19))
    );
  }
  if (net.isIP(address) === 6) {
    const value = address.toLowerCase().split("%")[0];
    if (value.startsWith("::ffff:")) return isPublicAddress(value.slice(7));
    return !(
      value === "::" || value === "::1" || value.startsWith("fc")
      || value.startsWith("fd") || /^fe[89ab]/.test(value)
      || value.startsWith("ff")
    );
  }
  return false;
}

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

function httpsRequest(url, options, records, requestBody = undefined) {
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
      if (response.statusCode >= 300 && response.statusCode < 400) {
        response.resume();
        const error = new Error("HTTP_REDIRECT_FORBIDDEN");
        error.code = "HTTP_REDIRECT_FORBIDDEN";
        reject(error);
        return;
      }
      const chunks = [];
      let size = 0;
      const limit = options?.responseType === "bytes"
        ? Number(request.maxMediaBytes || 512 * 1024 * 1024)
        : Number(request.maxOutputBytes || 4 * 1024 * 1024);
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
        if (!isPublicAddress(socket.remoteAddress) || !allowedAddresses.has(socket.remoteAddress)) {
          requestHandle.destroy(Object.assign(new Error("HTTP_PEER_ADDRESS_MISMATCH"), { code: "HTTP_PEER_ADDRESS_MISMATCH" }));
        }
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

const declaredInputUrls = new Set(
  (Array.isArray(request.payload?.request?.input_images)
    ? request.payload.request.input_images
    : [])
    .filter(value => typeof value === "string" && value.startsWith("https://")),
);

async function downloadDeclaredInput(value) {
  const raw = String(value || "");
  if (!declaredInputUrls.has(raw)) {
    const error = new Error("HTTP_DESTINATION_NOT_ALLOWED");
    error.code = "HTTP_DESTINATION_NOT_ALLOWED";
    throw error;
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
  );
  if (response.statusCode < 200 || response.statusCode >= 300) {
    const error = new Error("PROVIDER_HTTP_ERROR");
    error.code = "PROVIDER_HTTP_ERROR";
    throw error;
  }
  const mediaType = String(response.headers["content-type"] || "").split(";", 1)[0].toLowerCase();
  if (!/^image\/(?:png|jpeg|webp)$/.test(mediaType)) {
    const error = new Error("SUPPLIER_INPUT_MEDIA_INVALID");
    error.code = "SUPPLIER_INPUT_MEDIA_INVALID";
    throw error;
  }
  return { buffer, mediaType };
}

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
  const url = new URL(String(options?.url || ""));
  if (url.protocol !== "https:" || url.port && url.port !== "443" || !allowedOrigins.has(url.origin)) {
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
    const files = Array.isArray(options.multipart.files) ? options.multipart.files : [];
    if (files.length === 0 || files.length > 16) {
      const error = new Error("SUPPLIER_MULTIPART_INVALID");
      error.code = "SUPPLIER_MULTIPART_INVALID";
      throw error;
    }
    const resolvedFiles = [];
    for (const [index, file] of files.entries()) {
      const downloaded = await downloadDeclaredInput(file?.url);
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
      Number(request.maxMediaBytes || 512 * 1024 * 1024),
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
    const error = new Error("PROVIDER_HTTP_ERROR");
    error.code = "PROVIDER_HTTP_ERROR";
    throw error;
  }
  if (options?.responseType === "bytes") {
    return writeMediaReference(
      buffer,
      response.headers["content-type"] || "application/octet-stream",
    );
  }
  try { return JSON.parse(buffer.toString("utf8")); }
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
    globalThis.__mediaQueue = [];
    const denyNetwork = async () => {
      const error = new Error(networkErrorCode);
      error.code = networkErrorCode;
      throw error;
    };
    const queueNetwork = options => new Promise((resolve, reject) => {
      globalThis.__httpQueue.push({ options, resolve, reject });
    });
    const queueMedia = options => new Promise((resolve, reject) => {
      globalThis.__mediaQueue.push({ options, resolve, reject });
    });
    globalThis.helpers = Object.freeze({
      http: Object.freeze({ request: executionMode ? queueNetwork : denyNetwork }),
      media: Object.freeze({
        decodeBase64: executionMode
          ? (value, mediaType) => queueMedia({ operation: "decodeBase64", value, mediaType })
          : denyNetwork,
      }),
      log: Object.freeze({ info: () => undefined, warning: () => undefined }),
    });
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
  respond({
    ok: true,
    workerProtocolVersion: "1",
    helperApiVersion: request.helperApiVersion,
    workerRuntimeVersion: process.version,
    value,
  });
} catch (error) {
  respond({
    ok: false,
    error: {
      code: error?.code || "SUPPLIER_EXECUTION_FAILED",
      message: error?.code || "supplier operation failed",
    },
  });
}
