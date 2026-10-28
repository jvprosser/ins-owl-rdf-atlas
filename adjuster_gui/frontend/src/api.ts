export interface KickoffResult {
  session_id: string;
  trace_id: string;
  conversation_id: string;
}

export interface EventsResult {
  trace_id: string;
  conversation_id: string;
  completed: boolean;
  answer: string | null;
  next_step: string | null;
  responses: string[];
}

export interface AgentConfig {
  baseUrl: string;
  token: string;
  workflowId: string;
}

const URL_KEY = "adjuster-gui-base-url";
const TOKEN_KEY = "adjuster-gui-token";
const WORKFLOW_ID_KEY = "adjuster-gui-workflow-id";
const DEFAULT_WORKFLOW_ID = "86f01f5a-c485-4c47-9182-30c844eeeaa2";
export const DEFAULT_BASE_URL =
  "https://workflow-86f01f5a-c485-4c47-9182-30c844eeeaa2.ml-dbfc64d1-783.go01-dem.ylcu-atmi.cloudera.site";
const LAYOUT_PREFIX = "adjuster-gui-layout:";

/** Page-relative URL. Absolute /paths miss the Cloudera AI Application prefix. */
function appUrl(path: string): string {
  return `${import.meta.env.BASE_URL}${path.replace(/^\//, "")}`;
}

export interface NodePosition {
  x: number;
  y: number;
}

export function layoutStorageKey(nodeIds: string[]): string {
  return LAYOUT_PREFIX + [...nodeIds].sort().join("\n");
}

export function loadLayout(key: string): Record<string, NodePosition> {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, NodePosition>;
    const layout: Record<string, NodePosition> = {};
    for (const [id, pos] of Object.entries(parsed)) {
      if (pos && typeof pos.x === "number" && typeof pos.y === "number") {
        layout[id] = { x: pos.x, y: pos.y };
      }
    }
    return layout;
  } catch {
    return {};
  }
}

export function saveLayout(key: string, layout: Record<string, NodePosition>): void {
  localStorage.setItem(key, JSON.stringify(layout));
}

export function loadConfig(): AgentConfig {
  return {
    baseUrl: localStorage.getItem(URL_KEY) ?? DEFAULT_BASE_URL,
    token: localStorage.getItem(TOKEN_KEY) ?? "",
    workflowId: localStorage.getItem(WORKFLOW_ID_KEY) ?? DEFAULT_WORKFLOW_ID,
  };
}

export function saveConfig(config: AgentConfig): void {
  localStorage.setItem(URL_KEY, config.baseUrl.trim());
  localStorage.setItem(TOKEN_KEY, config.token.trim());
  localStorage.setItem(WORKFLOW_ID_KEY, config.workflowId.trim());
}

async function errorText(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    /* non-JSON */
  }
  return `${fallback} (${res.status})`;
}

export async function loadClaims(): Promise<string[]> {
  const res = await fetch(appUrl("/claims.json"));
  if (!res.ok) throw new Error(await errorText(res, "Failed to load claims"));
  const body = (await res.json()) as { claims?: string[] };
  return body.claims ?? [];
}

export async function loadSampleBpmn(): Promise<string> {
  const res = await fetch(appUrl("/sample/claims_playbook.bpmn"));
  if (!res.ok) throw new Error(await errorText(res, "Failed to load sample BPMN"));
  return res.text();
}

export async function saveBpmnLayout(positions: Record<string, NodePosition>): Promise<void> {
  const res = await fetch(appUrl("/sample/claims_playbook.bpmn"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ positions }),
  });
  if (!res.ok) throw new Error(await errorText(res, "Failed to save BPMN"));
}

export async function kickoffMessage(config: AgentConfig, userInput: string): Promise<KickoffResult> {
  const res = await fetch(appUrl("/api/agent/kickoff"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      base_url: config.baseUrl,
      token: config.token,
      user_input: userInput,
      workflow_id: config.workflowId ?? DEFAULT_WORKFLOW_ID,
    }),
  });
  if (!res.ok) throw new Error(await errorText(res, "Kickoff failed"));
  return res.json();
}

export async function streamEvents(
  config: AgentConfig,
  traceId: string,
  onUpdate: (update: EventsResult) => void
): Promise<void> {
  const params = new URLSearchParams({
    base_url: config.baseUrl,
    trace_id: traceId,
  });
  const res = await fetch(appUrl(`/api/agent/events/stream?${params}`), {
    headers: { "X-Workflow-Token": config.token },
  });
  if (!res.ok) throw new Error(await errorText(res, "Event stream failed"));
  if (!res.body) throw new Error("Event stream failed");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const take = (line: string) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    const update = JSON.parse(trimmed) as EventsResult & { error?: string };
    if (update.error) throw new Error(update.error);
    onUpdate(update);
  };
  while (true) {
    const chunk = await reader.read();
    if (chunk.done) break;
    buffer += decoder.decode(chunk.value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) take(line);
  }
  buffer += decoder.decode();
  if (buffer.trim()) take(buffer);
}

export async function pollEvents(
  config: AgentConfig,
  conversationId: string
): Promise<EventsResult> {
  const params = new URLSearchParams({
    base_url: config.baseUrl,
    conversation_id: conversationId,
  });
  const res = await fetch(appUrl(`/api/agent/events?${params}`), {
    headers: { "X-Workflow-Token": config.token },
  });
  if (!res.ok) throw new Error(await errorText(res, "Event poll failed"));
  return res.json();
}
