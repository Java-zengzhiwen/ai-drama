import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import { App } from "./App";

describe("App routes", () => {
  afterEach(() => {
    window.history.replaceState({}, "", "/");
  });

  test("/projects renders the project list shell", () => {
    window.history.replaceState({}, "", "/projects");

    render(<App />);

    expect(screen.getByRole("heading", { name: "项目列表" })).toBeInTheDocument();
    expect(screen.getByText("项目")).toBeInTheDocument();
  });

  test("unknown routes redirect to /projects", async () => {
    window.history.replaceState({}, "", "/missing-route");

    render(<App />);

    await waitFor(() => expect(window.location.pathname).toBe("/projects"));
    expect(screen.getByRole("heading", { name: "项目列表" })).toBeInTheDocument();
  });
});
