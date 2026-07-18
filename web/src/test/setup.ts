import "@testing-library/jest-dom/vitest";
import "../../../worker/src/network-denial.mjs";

if (!window.matchMedia) {
  window.matchMedia = () => ({
    matches: false,
    media: "",
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  });
}

const originalGetComputedStyle = window.getComputedStyle.bind(window);
window.getComputedStyle = ((element: Element, _pseudoElt?: string | null) =>
  originalGetComputedStyle(element)) as typeof window.getComputedStyle;
