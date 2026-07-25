import { InfoCircleFilled } from "@ant-design/icons";
import { Button } from "antd";
import { useState } from "react";

type WorkflowGateBarProps = {
  details: string[];
  summary: string;
};

export function WorkflowGateBar({ details, summary }: WorkflowGateBarProps) {
  const [expanded, setExpanded] = useState(false);
  return (
    <section aria-label="流程门" className="workflow-gate-bar" data-expanded={expanded}>
      <InfoCircleFilled aria-hidden="true" />
      <strong>流程门</strong>
      <span>{summary}</span>
      {details.length ? (
        <Button aria-expanded={expanded} onClick={() => setExpanded((value) => !value)} size="small" type="text">
          {expanded ? "收起原因" : "查看原因"}
        </Button>
      ) : null}
      {!expanded && details.length ? (
        <>
          {details.map((detail) => <span hidden key={detail}>{detail}</span>)}
        </>
      ) : null}
      {expanded ? <ul>{details.map((detail) => <li key={detail}>{detail}</li>)}</ul> : null}
    </section>
  );
}
