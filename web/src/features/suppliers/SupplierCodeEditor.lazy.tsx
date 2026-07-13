import { lazy } from "react";

export const LazySupplierCodeEditor = lazy(async () => {
  const module = await import("./SupplierCodeEditor");
  return { default: module.SupplierCodeEditor };
});
