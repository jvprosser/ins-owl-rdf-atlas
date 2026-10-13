import { Handle, Position, type NodeProps } from "@xyflow/react";

export interface FlowNodeData {
  label: string;
  bpmnType: string;
  category: "event" | "task" | "gateway";
  current: boolean;
  [key: string]: unknown;
}

export default function FlowNode({ data }: NodeProps) {
  const d = data as FlowNodeData;
  return (
    <div
      className={`bpmn-node bpmn-node--${d.category}${d.current ? " is-current" : ""}`}
    >
      <Handle type="target" position={Position.Left} isConnectable={false} />
      <span className="bpmn-node__type">{d.bpmnType}</span>
      <span>{d.label}</span>
      <Handle type="source" position={Position.Right} isConnectable={false} />
    </div>
  );
}
