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
}

const URL_KEY = "adjuster-gui-base-url";
const TOKEN_KEY = "adjuster-gui-token";
const LAYOUT_PREFIX = "adjuster-gui-layout:";

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
    baseUrl: localStorage.getItem(URL_KEY) ?? "",
    token: localStorage.getItem(TOKEN_KEY) ?? "",
  };
}

export function saveConfig(config: AgentConfig): void {
  localStorage.setItem(URL_KEY, config.baseUrl.trim());
  localStorage.setItem(TOKEN_KEY, config.token.trim());
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
  const res = await fetch("/claims.json");
  if (!res.ok) throw new Error(await errorText(res, "Failed to load claims"));
  const body = (await res.json()) as { claims?: string[] };
  return body.claims ?? [];
}

export async function loadSampleBpmn(): Promise<string> {
  const res = await fetch("/sample/claims_playbook.bpmn");
  if (!res.ok) throw new Error(await errorText(res, "Failed to load sample BPMN"));
  return res.text();
}

export async function kickoffMessage(config: AgentConfig, userInput: string): Promise<KickoffResult> {
  const res = await fetch("/api/agent/kickoff", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      base_url: config.baseUrl,
      token: config.token,
      user_input: userInput,
    }),
  });
  if (!res.ok) throw new Error(await errorText(res, "Kickoff failed"));
  return res.json();
}

export async function pollEvents(
  config: AgentConfig,
  conversationId: string
): Promise<EventsResult> {
  const params = new URLSearchParams({
    base_url: config.baseUrl,
    conversation_id: conversationId,
  });
  const res = await fetch(`/api/agent/events?${params}`, {
    headers: { "X-Workflow-Token": config.token },
  });
  if (!res.ok) throw new Error(await errorText(res, "Event poll failed"));
  return res.json();
}
