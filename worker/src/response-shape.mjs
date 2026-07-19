const valueType = value => (
  Array.isArray(value) ? "array" : value === null ? "null" : typeof value
);


export function describeResponseShape({ statusCode, contentType, byteLength, parsed }) {
  const output = Array.isArray(parsed?.output) ? parsed.output : [];
  const content = output.flatMap(item => (
    Array.isArray(item?.content) ? item.content : []
  ));

  return Object.freeze({
    schema: "provider-response-shape-v1",
    httpStatus: Number(statusCode || 0),
    contentType: String(contentType || "").split(";", 1)[0].toLowerCase(),
    byteLength: Number(byteLength || 0),
    bodyType: valueType(parsed),
    topLevelKeys: parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? Object.keys(parsed).sort()
      : [],
    statusType: valueType(parsed?.status),
    outputCount: output.length,
    outputItemTypes: output.map(item => String(item?.type || valueType(item))),
    contentItemTypes: content.map(item => String(item?.type || valueType(item))),
    contentFieldNames: [...new Set(content.flatMap(item => (
      item && typeof item === "object" ? Object.keys(item) : []
    )))].sort(),
    usageFieldNames: parsed?.usage && typeof parsed.usage === "object"
      ? Object.keys(parsed.usage).sort()
      : [],
  });
}


export function supplierErrorWithHostEvidence(error, hostEvidence) {
  const code = error?.code || "SUPPLIER_EXECUTION_FAILED";
  return Object.freeze({
    code,
    message: code,
    evidence: hostEvidence && typeof hostEvidence === "object" ? hostEvidence : null,
  });
}
