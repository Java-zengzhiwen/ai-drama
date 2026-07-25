const SAFE_FIELDS = new Set(["model", "prompt", "size", "quality", "n"]);
const SAFE_FILE_FIELDS = new Set(["image", "image[]"]);

function codedError(code) {
  return Object.assign(new Error(code), { code });
}

export function validateImageBuffer(buffer, mediaType) {
  const valid = (
    mediaType === "image/png"
      ? buffer.length >= 8 && buffer.subarray(0, 8).equals(Buffer.from("89504e470d0a1a0a", "hex"))
      : mediaType === "image/jpeg"
        ? buffer.length >= 3 && buffer[0] === 0xff && buffer[1] === 0xd8 && buffer[2] === 0xff
        : mediaType === "image/webp"
          ? buffer.length >= 12 && buffer.subarray(0, 4).toString("ascii") === "RIFF" && buffer.subarray(8, 12).toString("ascii") === "WEBP"
          : false
  );
  if (!valid) throw codedError("PROVIDER_RESPONSE_MALFORMED");
  return buffer;
}

export function validateOperationMediaBuffer(buffer, mediaType, operation) {
  const normalized = String(mediaType || "").split(";", 1)[0].toLowerCase();
  if (operation === "imageRequest") {
    if (!/^image\/(?:png|jpeg|webp)$/.test(normalized)) {
      throw codedError("PROVIDER_RESPONSE_MALFORMED");
    }
    return validateImageBuffer(buffer, normalized);
  }
  if (operation === "videoFetch") {
    const validMp4 = (
      normalized === "video/mp4"
      && buffer.length >= 12
      && buffer.subarray(4, 8).toString("ascii") === "ftyp"
    );
    if (!validMp4) throw codedError("PROVIDER_RESPONSE_MALFORMED");
  }
  return buffer;
}

export function decodeBase64(value, mediaType, maxBytes) {
  if (
    typeof value !== "string"
    || value.length === 0
    || !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(value)
  ) {
    throw codedError("PROVIDER_RESPONSE_MALFORMED");
  }
  const decoded = Buffer.from(value, "base64");
  if (decoded.length > Number(maxBytes)) {
    throw codedError("SUPPLIER_WORKER_OUTPUT_TOO_LARGE");
  }
  return validateImageBuffer(decoded, String(mediaType || "").toLowerCase());
}

export function decodeDeclaredImageReference(value, maxBytes) {
  const match = /^data:(image\/(?:png|jpeg|webp));base64,([A-Za-z0-9+/=]+)$/i.exec(
    String(value || ""),
  );
  if (!match) throw codedError("SUPPLIER_INPUT_MEDIA_INVALID");
  return {
    mediaType: match[1].toLowerCase(),
    buffer: decodeBase64(match[2], match[1].toLowerCase(), maxBytes),
  };
}

const MEDIA_URL_FIELDS = new Set(["url", "image_url", "video_url"]);

export function collectProviderResultUrls(value, output = []) {
  if (Array.isArray(value)) {
    for (const item of value) collectProviderResultUrls(item, output);
  } else if (value && typeof value === "object") {
    for (const [key, item] of Object.entries(value)) {
      if (MEDIA_URL_FIELDS.has(key) && typeof item === "string" && item.startsWith("https://")) {
        output.push(item);
      } else if (item && typeof item === "object") {
        collectProviderResultUrls(item, output);
      }
    }
  }
  return output;
}

export function authorizeProviderResultDownload(options, allowedUrls) {
  const raw = String(options?.url || "");
  const clean = (
    String(options?.method || "GET").toUpperCase() === "GET"
    && options?.responseType === "bytes"
    && Object.keys(options?.headers || {}).length === 0
    && Object.keys(options?.query || {}).length === 0
    && options?.body === undefined
    && options?.multipart === undefined
    && allowedUrls.has(raw)
  );
  if (!clean) throw codedError("HTTP_DESTINATION_NOT_ALLOWED");
  allowedUrls.delete(raw);
  return true;
}

export function authorizeDeclaredInputReference(value, declaredReferences) {
  const raw = String(value || "");
  if (!declaredReferences.has(raw)) throw codedError("HTTP_DESTINATION_NOT_ALLOWED");
  return raw;
}

export function assertInputBudget(currentBytes, nextBytes, limitBytes) {
  const total = Number(currentBytes) + Number(nextBytes);
  if (!Number.isSafeInteger(total) || total < 0 || total > Number(limitBytes)) {
    throw codedError("SUPPLIER_WORKER_OUTPUT_TOO_LARGE");
  }
  return total;
}

export function providerHttpErrorCode(statusCode) {
  const status = Number(statusCode);
  if (status === 401 || status === 403) return "PROVIDER_AUTHENTICATION_ERROR";
  if (status === 404) return "PROVIDER_ROUTE_OR_MODEL_NOT_FOUND";
  if (status === 429) return "PROVIDER_RATE_LIMITED";
  if (status >= 400 && status < 500) return "PROVIDER_REQUEST_REJECTED";
  if (status >= 500 && status < 600) return "PROVIDER_UPSTREAM_ERROR";
  return "PROVIDER_HTTP_ERROR";
}

function safeToken(value, code = "SUPPLIER_MULTIPART_INVALID") {
  const token = String(value || "");
  if (!token || /[\r\n"\\]/.test(token)) throw codedError(code);
  return token;
}

export function buildMultipartBody(spec, boundary, maxBytes) {
  const marker = safeToken(boundary);
  const chunks = [];
  let totalBytes = 0;
  const append = chunk => {
    totalBytes = assertInputBudget(totalBytes, chunk.length, Number(maxBytes));
    chunks.push(chunk);
  };
  for (const [name, rawValue] of Object.entries(spec?.fields || {})) {
    if (!SAFE_FIELDS.has(name) || rawValue === undefined || rawValue === null) {
      throw codedError("SUPPLIER_MULTIPART_INVALID");
    }
    append(Buffer.from(
      `--${marker}\r\nContent-Disposition: form-data; name="${name}"\r\n\r\n${String(rawValue)}\r\n`,
      "utf8",
    ));
  }
  for (const file of spec?.files || []) {
    const fieldName = safeToken(file?.fieldName);
    if (!SAFE_FILE_FIELDS.has(fieldName) || !Buffer.isBuffer(file?.data)) {
      throw codedError("SUPPLIER_MULTIPART_INVALID");
    }
    const filename = safeToken(file.filename);
    const mediaType = safeToken(file.mediaType);
    if (!/^image\/(?:png|jpeg|webp)$/.test(mediaType)) {
      throw codedError("SUPPLIER_INPUT_MEDIA_INVALID");
    }
    append(Buffer.from(
      `--${marker}\r\nContent-Disposition: form-data; name="${fieldName}"; filename="${filename}"\r\nContent-Type: ${mediaType}\r\n\r\n`,
      "utf8",
    ));
    append(file.data);
    append(Buffer.from("\r\n", "utf8"));
  }
  append(Buffer.from(`--${marker}--\r\n`, "utf8"));
  return Buffer.concat(chunks, totalBytes);
}
