import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { WorkflowGateBar } from "./WorkflowGateBar";

describe("WorkflowGateBar", () => {
  test("keeps reasons compact until the user asks to see them", () => {
    render(
      <WorkflowGateBar
        details={["未确认剧本，不允许生成分镜。"]}
        summary="确认剧本后可继续分镜"
      />,
    );

    const gate = screen.getByRole("region", { name: "流程门" });
    expect(gate).toHaveAttribute("data-expanded", "false");
    expect(screen.getByText("确认剧本后可继续分镜")).toBeVisible();
    expect(screen.queryByText("未确认剧本，不允许生成分镜。")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "查看原因" }));
    expect(gate).toHaveAttribute("data-expanded", "true");
    expect(screen.getByText("未确认剧本，不允许生成分镜。")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "收起原因" }));
    expect(gate).toHaveAttribute("data-expanded", "false");
  });
});
