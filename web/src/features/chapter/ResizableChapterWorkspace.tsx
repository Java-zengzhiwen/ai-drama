import { MenuOutlined, ProfileOutlined } from "@ant-design/icons";
import { Button, Drawer } from "antd";
import type { CSSProperties, KeyboardEvent, PointerEvent, ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import {
  MAX_LEFT_RATIO,
  MAX_RIGHT_RATIO,
  MIN_CENTER_RATIO,
  MIN_LEFT_RATIO,
  MIN_RIGHT_RATIO,
  centerRatio,
  clampPaneRatios,
  moveDivider,
  type PaneRatios,
  type WorkspaceDivider,
} from "./workspaceLayout";
import { useWorkspacePaneRatios } from "./useWorkspacePaneRatios";

type WorkspaceProps = {
  center: ReactNode;
  left: ReactNode;
  leftDrawerTitle: string;
  right: ReactNode;
  rightDrawerTitle: string;
};

type WorkspaceStyle = CSSProperties & {
  "--workspace-center": string;
  "--workspace-left": string;
  "--workspace-right": string;
};

type DragState = {
  divider: WorkspaceDivider;
  startRatios: PaneRatios;
  startX: number;
};

export function ResizableChapterWorkspace({
  center,
  left,
  leftDrawerTitle,
  right,
  rightDrawerTitle,
}: WorkspaceProps) {
  const { commit, compact, preview, ratios, reset, viewportWidth } = useWorkspacePaneRatios();
  const [openDrawer, setOpenDrawer] = useState<WorkspaceDivider | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<DragState | null>(null);
  const ratiosRef = useRef(ratios);
  const leftTriggerRef = useRef<HTMLButtonElement>(null);
  const rightTriggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    ratiosRef.current = ratios;
  }, [ratios]);

  useEffect(() => {
    if (compact) setOpenDrawer(null);
  }, [compact]);

  useEffect(() => {
    if (!compact || openDrawer === null) return;
    const closeOnEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      const closingDrawer = openDrawer;
      setOpenDrawer(null);
      window.requestAnimationFrame(() => {
        (closingDrawer === "left" ? leftTriggerRef.current : rightTriggerRef.current)?.focus();
      });
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [compact, openDrawer]);

  function setDrawer(next: WorkspaceDivider | null) {
    const previous = openDrawer;
    setOpenDrawer(next);
    if (next === null) {
      window.requestAnimationFrame(() => {
        (previous === "left" ? leftTriggerRef.current : rightTriggerRef.current)?.focus();
      });
    }
  }

  function handlePointerDown(divider: WorkspaceDivider, event: PointerEvent<HTMLButtonElement>) {
    const rootWidth = rootRef.current?.getBoundingClientRect().width ?? 0;
    if (!rootWidth) return;
    dragRef.current = { divider, startRatios: ratiosRef.current, startX: event.clientX };
    event.currentTarget.dataset.dragging = "true";
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event: PointerEvent<HTMLButtonElement>) {
    const drag = dragRef.current;
    const rootWidth = rootRef.current?.getBoundingClientRect().width ?? 0;
    if (!drag || !rootWidth) return;
    const delta = ((event.clientX - drag.startX) / rootWidth) * 100;
    const next = moveDivider(drag.startRatios, drag.divider, delta, viewportWidth);
    ratiosRef.current = next;
    preview(next);
  }

  function handlePointerUp(event: PointerEvent<HTMLButtonElement>) {
    if (!dragRef.current) return;
    dragRef.current = null;
    delete event.currentTarget.dataset.dragging;
    event.currentTarget.releasePointerCapture(event.pointerId);
    commit(ratiosRef.current);
  }

  function handlePointerCancel(event: PointerEvent<HTMLButtonElement>) {
    const drag = dragRef.current;
    if (!drag) return;
    dragRef.current = null;
    delete event.currentTarget.dataset.dragging;
    ratiosRef.current = drag.startRatios;
    preview(drag.startRatios);
  }

  function handleKeyDown(divider: WorkspaceDivider, event: KeyboardEvent<HTMLButtonElement>) {
    const step = event.shiftKey ? 5 : 1;
    let next: PaneRatios | null = null;
    if (event.key === "ArrowLeft") {
      next = moveDivider(ratios, divider, divider === "left" ? -step : -step, viewportWidth);
    } else if (event.key === "ArrowRight") {
      next = moveDivider(ratios, divider, divider === "left" ? step : step, viewportWidth);
    } else if (event.key === "Home") {
      next = clampPaneRatios(
        divider === "left" ? { ...ratios, left: MIN_LEFT_RATIO } : { ...ratios, right: MIN_RIGHT_RATIO },
        viewportWidth,
      );
    } else if (event.key === "End") {
      next = clampPaneRatios(
        divider === "left" ? { ...ratios, left: MAX_LEFT_RATIO } : { ...ratios, right: MAX_RIGHT_RATIO },
        viewportWidth,
      );
    }
    if (next) {
      event.preventDefault();
      commit(next);
    }
  }

  if (compact) {
    return (
      <section className="chapter-workspace-compact" data-testid="resizable-chapter-workspace">
        <div className="chapter-workspace-compact-actions">
          <Button
            aria-label={`打开${leftDrawerTitle}`}
            icon={<MenuOutlined />}
            onClick={() => setDrawer("left")}
            ref={leftTriggerRef}
          >
            {leftDrawerTitle}
          </Button>
          <Button
            aria-label={`打开${rightDrawerTitle}`}
            icon={<ProfileOutlined />}
            onClick={() => setDrawer("right")}
            ref={rightTriggerRef}
          >
            {rightDrawerTitle}
          </Button>
        </div>
        <div className="chapter-workspace-center" data-workspace-pane="center">
          {center}
        </div>
        <Drawer
          className="workspace-pane-drawer"
          destroyOnHidden
          onClose={() => setDrawer(null)}
          open={openDrawer === "left"}
          placement="left"
          title={leftDrawerTitle}
          width="min(360px, 92vw)"
        >
          {left}
        </Drawer>
        <Drawer
          className="workspace-pane-drawer"
          destroyOnHidden
          onClose={() => setDrawer(null)}
          open={openDrawer === "right"}
          placement="right"
          title={rightDrawerTitle}
          width="min(420px, 92vw)"
        >
          {right}
        </Drawer>
      </section>
    );
  }

  const style: WorkspaceStyle = {
    "--workspace-left": `${ratios.left}%`,
    "--workspace-center": `${centerRatio(ratios)}%`,
    "--workspace-right": `${ratios.right}%`,
  };

  return (
    <div className="resizable-chapter-workspace" data-testid="resizable-chapter-workspace" ref={rootRef} style={style}>
      <aside aria-label={leftDrawerTitle} className="chapter-workspace-left" data-workspace-pane="left">
        {left}
      </aside>
      <WorkspaceSeparator
        divider="left"
        label="调整章节导航宽度"
        onDoubleClick={reset}
        onKeyDown={handleKeyDown}
        onPointerDown={handlePointerDown}
        onPointerCancel={handlePointerCancel}
        onLostPointerCapture={handlePointerCancel}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        value={ratios.left}
        maximum={Math.min(MAX_LEFT_RATIO, 100 - MIN_CENTER_RATIO - ratios.right)}
      />
      <div className="chapter-workspace-center" data-workspace-pane="center">
        {center}
      </div>
      <WorkspaceSeparator
        divider="right"
        label="调整详情栏宽度"
        onDoubleClick={reset}
        onKeyDown={handleKeyDown}
        onPointerDown={handlePointerDown}
        onPointerCancel={handlePointerCancel}
        onLostPointerCapture={handlePointerCancel}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        value={ratios.right}
        maximum={Math.min(MAX_RIGHT_RATIO, 100 - MIN_CENTER_RATIO - ratios.left)}
      />
      <aside aria-label={rightDrawerTitle} className="chapter-workspace-right" data-workspace-pane="right">
        {right}
      </aside>
    </div>
  );
}

type WorkspaceSeparatorProps = {
  divider: WorkspaceDivider;
  label: string;
  onDoubleClick: () => void;
  onKeyDown: (divider: WorkspaceDivider, event: KeyboardEvent<HTMLButtonElement>) => void;
  onPointerDown: (divider: WorkspaceDivider, event: PointerEvent<HTMLButtonElement>) => void;
  onPointerCancel: (event: PointerEvent<HTMLButtonElement>) => void;
  onLostPointerCapture: (event: PointerEvent<HTMLButtonElement>) => void;
  onPointerMove: (event: PointerEvent<HTMLButtonElement>) => void;
  onPointerUp: (event: PointerEvent<HTMLButtonElement>) => void;
  value: number;
  maximum: number;
};

function WorkspaceSeparator({
  divider,
  label,
  onDoubleClick,
  onKeyDown,
  onPointerDown,
  onPointerCancel,
  onLostPointerCapture,
  onPointerMove,
  onPointerUp,
  value,
  maximum,
}: WorkspaceSeparatorProps) {
  const minimum = divider === "left" ? MIN_LEFT_RATIO : MIN_RIGHT_RATIO;
  return (
    <button
      aria-label={label}
      aria-orientation="vertical"
      aria-valuemax={maximum}
      aria-valuemin={minimum}
      aria-valuenow={value}
      className="workspace-separator"
      data-divider={divider}
      onDoubleClick={onDoubleClick}
      onKeyDown={(event) => onKeyDown(divider, event)}
      onPointerDown={(event) => onPointerDown(divider, event)}
      onPointerCancel={onPointerCancel}
      onLostPointerCapture={onLostPointerCapture}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      role="separator"
      type="button"
    />
  );
}
