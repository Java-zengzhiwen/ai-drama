import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi, type Mock } from "vitest";
import { apiClient } from "../api/client";
import { App } from "./App";

vi.mock("../api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockedGet = apiClient.get as unknown as Mock;
const mockedPost = apiClient.post as unknown as Mock;

describe("App routes", () => {
  beforeEach(() => {
    mockedGet.mockResolvedValue({ data: [] });
    mockedPost.mockReset();
  });

  afterEach(() => {
    mockedGet.mockReset();
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

  test("/suppliers renders the local supplier management destination", async () => {
    window.history.replaceState({}, "", "/suppliers");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "模型供应商" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "模型供应商" })).toHaveAttribute(
      "href",
      "/suppliers",
    );
  });
});
