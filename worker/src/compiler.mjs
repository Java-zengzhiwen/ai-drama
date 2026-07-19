import vm from "node:vm";
import * as esbuild from "esbuild";


function fail(code, message, location = {}) {
  process.stdout.write(JSON.stringify({
    ok: false,
    error: {
      code,
      message: String(message).slice(0, 299),
      line: location.line || 0,
      column: (location.column || 0) + 1,
    },
  }));
  process.exit(0);
}


function validateVendor(vendor) {
  if (!vendor || typeof vendor !== "object") return false;
  for (const key of ["id", "version", "name", "author"]) {
    if (typeof vendor[key] !== "string" || !vendor[key]) return false;
  }
  if (vendor.adapterContractVersion !== "ai-drama-supplier-v1") return false;
  if (!["ai-drama-helper-v1", "ai-drama-helper-v2"].includes(vendor.helperApiVersion)) return false;
  if (!/^[a-z0-9][a-z0-9._:-]{0,127}$/.test(vendor.rateLimitBucketKey || "")) return false;
  return Array.isArray(vendor.inputs)
    && vendor.inputs.every(validateInput)
    && vendor.inputValues
    && Array.isArray(vendor.models);
}


function validateInput(input) {
  if (!input || typeof input !== "object") return false;
  const identity = input.key || input.name || input.id;
  if (typeof identity !== "string" || !identity) return false;
  if (input.type !== "select") return true;
  if (!Array.isArray(input.options) || input.options.length === 0) return false;
  const values = input.options.map(option => option?.value);
  return values.every(value => typeof value === "string" && value.length > 0)
    && new Set(values).size === values.length
    && input.options.every(
      option => typeof option?.label === "string" && option.label.length > 0,
    );
}


let input;
try {
  input = JSON.parse(await new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", chunk => data += chunk);
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  }));
} catch {
  fail("SUPPLIER_COMPILER_PROTOCOL_ERROR", "invalid compiler request");
}

let result;
try {
  result = await esbuild.build({
    stdin: {
      contents: input.source,
      loader: "ts",
      sourcefile: "supplier.ts",
    },
    bundle: true,
    write: false,
    format: "cjs",
    platform: "neutral",
    target: "es2022",
    legalComments: "none",
    sourcemap: false,
    logLevel: "silent",
  });
} catch (error) {
  const detail = error.errors?.[0] || {};
  fail("TYPESCRIPT_COMPILE_FAILED", detail.text || "TypeScript compilation failed", detail.location);
}

const compiledCode = result.outputFiles[0].text;
const context = vm.createContext({}, { codeGeneration: { strings: false, wasm: false } });
let vendor;
let runtimeExports;
try {
  new vm.Script(
    "globalThis.module = { exports: {} }; globalThis.exports = globalThis.module.exports;",
    { filename: "supplier-bootstrap.cjs" },
  ).runInContext(context, { timeout: 1000 });
  new vm.Script(compiledCode, { filename: "supplier.cjs" }).runInContext(context, { timeout: 1000 });
  const vendorJson = new vm.Script(
    "JSON.stringify(module.exports.vendor)",
    { filename: "supplier-manifest.cjs" },
  ).runInContext(context, { timeout: 1000 });
  vendor = vendorJson ? JSON.parse(vendorJson) : undefined;
  const exportsJson = new vm.Script(
    "JSON.stringify(Object.keys(module.exports))",
    { filename: "supplier-exports.cjs" },
  ).runInContext(context, { timeout: 1000 });
  runtimeExports = JSON.parse(exportsJson);
} catch {
  fail("SUPPLIER_VALIDATION_FAILED", "supplier module failed local validation");
}
if (!vendor) fail("MISSING_VENDOR_EXPORT", "supplier must export vendor");
if (!validateVendor(vendor)) fail("INVALID_VENDOR_MANIFEST", "vendor manifest is invalid");
const requiredExports = {
  text: ["textRequest"],
  image: ["imageRequest"],
  video: ["videoSubmit", "videoPoll", "videoFetch"],
};
for (const model of vendor.models) {
  for (const exportName of requiredExports[model.capability] || []) {
    if (!runtimeExports.includes(exportName)) {
      fail("MISSING_RUNTIME_EXPORT", "supplier is missing required runtime export");
    }
  }
}

process.stdout.write(JSON.stringify({
  ok: true,
  compilerVersion: esbuild.version,
  workerRuntimeVersion: process.version,
  compiledCode,
  vendor,
}));
