const SAFE_FIELDS = new Set(["model", "prompt", "size", "quality", "n"]);
const SAFE_FILE_FIELDS = new Set(["image", "image[]"]);

function codedError(code) {
  return Object.assign(new Error(code), { code });
}

export function decodeBase64(value, maxBytes) {
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
  return decoded;
}

export function decodeDeclaredImageReference(value, maxBytes) {
  const match = /^data:(image\/(?:png|jpeg|webp));base64,([A-Za-z0-9+/=]+)$/i.exec(
    String(value || ""),
  );
  if (!match) throw codedError("SUPPLIER_INPUT_MEDIA_INVALID");
  return {
    mediaType: match[1].toLowerCase(),
    buffer: decodeBase64(match[2], maxBytes),
  };
}

export function collectHttpsUrls(value, output = []) {
  if (typeof value === "string") {
    if (value.startsWith("https://")) output.push(value);
  } else if (Array.isArray(value)) {
    for (const item of value) collectHttpsUrls(item, output);
  } else if (value && typeof value === "object") {
    for (const item of Object.values(value)) collectHttpsUrls(item, output);
  }
  return output;
}

function safeToken(value, code = "SUPPLIER_MULTIPART_INVALID") {
  const token = String(value || "");
  if (!token || /[\r\n"\\]/.test(token)) throw codedError(code);
  return token;
}

export function buildMultipartBody(spec, boundary, maxBytes) {
  const marker = safeToken(boundary);
  const chunks = [];
  for (const [name, rawValue] of Object.entries(spec?.fields || {})) {
    if (!SAFE_FIELDS.has(name) || rawValue === undefined || rawValue === null) {
      throw codedError("SUPPLIER_MULTIPART_INVALID");
    }
    chunks.push(Buffer.from(
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
    chunks.push(Buffer.from(
      `--${marker}\r\nContent-Disposition: form-data; name="${fieldName}"; filename="${filename}"\r\nContent-Type: ${mediaType}\r\n\r\n`,
      "utf8",
    ));
    chunks.push(file.data);
    chunks.push(Buffer.from("\r\n", "utf8"));
  }
  chunks.push(Buffer.from(`--${marker}--\r\n`, "utf8"));
  const body = Buffer.concat(chunks);
  if (body.length > Number(maxBytes)) {
    throw codedError("SUPPLIER_WORKER_OUTPUT_TOO_LARGE");
  }
  return body;
}
