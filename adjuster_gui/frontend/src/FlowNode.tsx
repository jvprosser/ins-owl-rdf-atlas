import { createContext, useContext, useEffect, useRef } from "react";
import { Handle, Position, useViewport, type NodeProps } from "@xyflow/react";

export interface FlowNodeData {
  label: string;
  bpmnType: string;
  category: "event" | "task" | "gateway";
  current: boolean;
  [key: string]: unknown;
}

export interface NodeDragHandlers {
  move: (id: string, position: { x: number; y: number }) => void;
  commit: () => void;
}

export const NodeDragContext = createContext<NodeDragHandlers | null>(null);

export default function FlowNode({
  id,
  data,
  positionAbsoluteX,
  positionAbsoluteY,
}: NodeProps) {
  const d = data as FlowNodeData;
  const dragApi = useContext(NodeDragContext);
  const { zoom } = useViewport();
  const rootRef = useRef<HTMLDivElement>(null);
  const dragApiRef = useRef(dragApi);
  const zoomRef = useRef(zoom);
  const positionRef = useRef({ x: positionAbsoluteX, y: positionAbsoluteY });
  dragApiRef.current = dragApi;
  zoomRef.current = zoom;
  positionRef.current = { x: positionAbsoluteX, y: positionAbsoluteY };

  useEffect(() => {
    const root = rootRef.current?.closest<HTMLElement>(".react-flow__node");
    if (!root) return;

    let drag: { pointerId: number; x: number; y: number; px: number; py: number } | null = null;

    const onPointerDown = (event: PointerEvent) => {
      if (event.button !== 0) return;
      // Chromium still delivers this gesture to the pane as a touch or mouse pan.
      event.preventDefault();
      event.stopPropagation();
      try {
        root.setPointerCapture(event.pointerId);
      } catch {
        // Synthetic events cannot capture the pointer.
      }
      drag = {
        pointerId: event.pointerId,
        x: event.clientX,
        y: event.clientY,
        px: positionRef.current.x,
        py: positionRef.current.y,
      };
    };

    const onPointerMove = (event: PointerEvent) => {
      if (!drag || event.pointerId !== drag.pointerId) return;
      event.preventDefault();
      event.stopPropagation();
      const scale = zoomRef.current || 1;
      dragApiRef.current?.move(id, {
        x: drag.px + (event.clientX - drag.x) / scale,
        y: drag.py + (event.clientY - drag.y) / scale,
      });
    };

    const endDrag = (event: PointerEvent) => {
      if (!drag || event.pointerId !== drag.pointerId) return;
      drag = null;
      if (root.hasPointerCapture(event.pointerId)) root.releasePointerCapture(event.pointerId);
      dragApiRef.current?.commit();
    };

    const blockPan = (event: Event) => {
      event.stopImmediatePropagation();
    };

    root.addEventListener("pointerdown", onPointerDown);
    root.addEventListener("pointermove", onPointerMove);
    root.addEventListener("pointerup", endDrag);
    root.addEventListener("pointercancel", endDrag);
    root.addEventListener("mousedown", blockPan, true);
    root.addEventListener("touchstart", blockPan, true);
    return () => {
      root.removeEventListener("pointerdown", onPointerDown);
      root.removeEventListener("pointermove", onPointerMove);
      root.removeEventListener("pointerup", endDrag);
      root.removeEventListener("pointercancel", endDrag);
      root.removeEventListener("mousedown", blockPan, true);
      root.removeEventListener("touchstart", blockPan, true);
    };
  }, [id]);

  return (
    <div
      ref={rootRef}
      className={`bpmn-node nopan bpmn-node--${d.category}${d.current ? " is-current" : ""}`}
    >
      <Handle type="target" position={Position.Left} isConnectable={false} />
      <span className="bpmn-node__type">{d.bpmnType}</span>
      <span>{d.label}</span>
      <Handle type="source" position={Position.Right} isConnectable={false} />
    </div>
  );
}
