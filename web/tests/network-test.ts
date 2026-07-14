import { expect, test as base, type BrowserContext } from "@playwright/test";

export { expect } from "@playwright/test";
export type { APIRequestContext, Locator, Page, Route } from "@playwright/test";

export const NETWORK_GUARD_PROBE_URL = "https://external.invalid/__network_guard_probe__";

function isLoopback(hostname: string): boolean {
  const host = hostname.replace(/^\[|\]$/g, "");
  return host === "localhost" || host === "::1" || /^127(?:\.|$)/.test(host);
}

export const test = base.extend<{ context: BrowserContext }>({
  context: async ({ context }, use) => {
    const unexpected: string[] = [];
    await context.route("**/*", async (route) => {
      const requestUrl = route.request().url();
      const url = new URL(requestUrl);
      if ((url.protocol === "http:" || url.protocol === "https:") && !isLoopback(url.hostname)) {
        await route.abort("blockedbyclient");
        if (requestUrl !== NETWORK_GUARD_PROBE_URL) unexpected.push(requestUrl);
        return;
      }
      await route.fallback();
    });

    await use(context);
    expect(unexpected, "non-loopback browser requests must be blocked before transport").toEqual([]);
  },
});
