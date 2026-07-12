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
  if (vendor.helperApiVersion !== "ai-drama-helper-v1") return false;
  if (!/^[a-z0-9][a-z0-9._:-]{0,127}$/.test(vendor.rateLimitBucketKey || "")) return false;
  return Array.isArray(vendor.inputs) && vendor.inputValues && Array.isArray(vendor.models);
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
const moduleObject = { exports: {} };
const context = vm.createContext({ module: moduleObject, exports: moduleObject.exports });
try {
  new vm.Script(compiledCode, { filename: "supplier.cjs" }).runInContext(context, { timeout: 1000 });
} catch {
  fail("SUPPLIER_VALIDATION_FAILED", "supplier module failed local validation");
}
const vendor = moduleObject.exports.vendor;
if (!vendor) fail("MISSING_VENDOR_EXPORT", "supplier must export vendor");
if (!validateVendor(vendor)) fail("INVALID_VENDOR_MANIFEST", "vendor manifest is invalid");

process.stdout.write(JSON.stringify({
  ok: true,
  compilerVersion: esbuild.version,
  compiledCode,
  vendor,
}));
