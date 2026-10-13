export interface BpmnNode {
  id: string;
  name: string;
  type: string;
  x: number;
  y: number;
}

export interface BpmnEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

export interface BpmnGraph {
  nodes: BpmnNode[];
  edges: BpmnEdge[];
}

const FLOW_NODES = new Set([
  "startEvent",
  "endEvent",
  "intermediateCatchEvent",
  "intermediateThrowEvent",
  "boundaryEvent",
  "task",
  "userTask",
  "serviceTask",
  "scriptTask",
  "businessRuleTask",
  "manualTask",
  "sendTask",
  "receiveTask",
  "callActivity",
  "subProcess",
  "exclusiveGateway",
  "parallelGateway",
  "inclusiveGateway",
  "complexGateway",
  "eventBasedGateway",
]);

function localName(el: Element): string {
  const name = el.localName || el.tagName;
  const brace = name.indexOf("}");
  const bare = brace >= 0 ? name.slice(brace + 1) : name;
  const colon = bare.indexOf(":");
  return colon >= 0 ? bare.slice(colon + 1) : bare;
}

function cascade(nodes: BpmnNode[], edges: BpmnEdge[]): void {
  const incoming = new Map<string, number>();
  for (const node of nodes) incoming.set(node.id, 0);
  for (const edge of edges) {
    incoming.set(edge.target, (incoming.get(edge.target) ?? 0) + 1);
  }
  const placed = new Set<string>();
  let column = 0;
  let frontier = nodes.filter((node) => (incoming.get(node.id) ?? 0) === 0).map((node) => node.id);
  if (frontier.length === 0 && nodes.length > 0) frontier = [nodes[0].id];
  const byId = new Map(nodes.map((node) => [node.id, node]));
  while (frontier.length > 0) {
    const next: string[] = [];
    frontier.forEach((id, row) => {
      const node = byId.get(id);
      if (!node || placed.has(id)) return;
      node.x = 40 + column * 220;
      node.y = 40 + row * 110;
      placed.add(id);
      for (const edge of edges) {
        if (edge.source === id && !placed.has(edge.target)) next.push(edge.target);
      }
    });
    frontier = [...new Set(next)];
    column += 1;
    if (column > nodes.length + 2) break;
  }
  let row = 0;
  for (const node of nodes) {
    if (placed.has(node.id)) continue;
    node.x = 40;
    node.y = 40 + row * 110;
    row += 1;
  }
}

export function parseBpmn(xml: string): BpmnGraph {
  const doc = new DOMParser().parseFromString(xml, "application/xml");
  if (doc.querySelector("parsererror")) {
    throw new Error("BPMN file is not valid XML");
  }
  const nodes: BpmnNode[] = [];
  const edges: BpmnEdge[] = [];
  const coords = new Map<string, { x: number; y: number }>();

  const all = doc.getElementsByTagName("*");
  for (let i = 0; i < all.length; i += 1) {
    const el = all[i];
    const tag = localName(el);
    if (tag === "BPMNShape") {
      const ref = el.getAttribute("bpmnElement");
      const bounds = [...el.children].find((child) => localName(child) === "Bounds");
      if (ref && bounds) {
        coords.set(ref, {
          x: Number(bounds.getAttribute("x") ?? 0),
          y: Number(bounds.getAttribute("y") ?? 0),
        });
      }
    }
    if (tag === "sequenceFlow") {
      const id = el.getAttribute("id");
      const source = el.getAttribute("sourceRef");
      const target = el.getAttribute("targetRef");
      if (id && source && target) {
        edges.push({
          id,
          source,
          target,
          label: el.getAttribute("name") ?? undefined,
        });
      }
    }
    if (FLOW_NODES.has(tag)) {
      const id = el.getAttribute("id");
      if (!id) continue;
      nodes.push({
        id,
        name: el.getAttribute("name") || id,
        type: tag,
        x: 0,
        y: 0,
      });
    }
  }

  let hasDi = false;
  for (const node of nodes) {
    const point = coords.get(node.id);
    if (!point) continue;
    node.x = point.x;
    node.y = point.y;
    hasDi = true;
  }
  if (!hasDi) cascade(nodes, edges);
  return { nodes, edges };
}

export function nodeMatchesStep(node: BpmnNode, step: string | null): boolean {
  if (!step) return false;
  return node.id === step || node.name === step;
}
