import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import ReactMarkdown from "react-markdown";
import {
  kickoffMessage,
  loadClaims,
  loadConfig,
  loadSampleBpmn,
  pollEvents,
  saveConfig,
  type AgentConfig,
} from "./api";
import { nodeMatchesStep, parseBpmn, type BpmnGraph } from "./bpmn";
import FlowNode, { type FlowNodeData } from "./FlowNode";

const POLL_MS = 2000;
const POLL_TIMEOUT_MS = 300_000;

interface ChatMessage {
  id: string;
  role: "user" | "agent";
  text: string;
  turnId?: string;
}

const CHAT_MIN = 260;

const nodeTypes = { bpmn: FlowNode };

function categoryOf(bpmnType: string): FlowNodeData["category"] {
  const t = bpmnType.toLowerCase();
  if (t.includes("gateway")) return "gateway";
  if (t.includes("event")) return "event";
  return "task";
}

function toFlow(graph: BpmnGraph, step: string | null): { nodes: Node[]; edges: Edge[] } {
  return {
    nodes: graph.nodes.map((node) => ({
      id: node.id,
      type: "bpmn",
      position: { x: node.x, y: node.y },
      data: {
        label: node.name,
        bpmnType: node.type,
        category: categoryOf(node.type),
        current: nodeMatchesStep(node, step),
      } satisfies FlowNodeData,
      draggable: false,
      connectable: false,
    })),
    edges: graph.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.label,
      deletable: false,
    })),
  };
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export default function App() {
  const [claims, setClaims] = useState<string[]>([]);
  const [graph, setGraph] = useState<BpmnGraph | null>(null);
  const [step, setStep] = useState<string | null>(null);
  const [activeClaim, setActiveClaim] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [composer, setComposer] = useState("");
  const [chatWidth, setChatWidth] = useState(340);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [draft, setDraft] = useState<AgentConfig>({ baseUrl: "", token: "" });
  const fileRef = useRef<HTMLInputElement>(null);
  const transcriptRef = useRef<HTMLDivElement>(null);
  const resizeRef = useRef<{ x: number; width: number } | null>(null);
  const configRef = useRef<AgentConfig>(loadConfig());

  useEffect(() => {
    const el = transcriptRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  useEffect(() => {
    const onMove = (event: PointerEvent) => {
      const drag = resizeRef.current;
      if (!drag) return;
      const max = Math.max(CHAT_MIN, window.innerWidth - 420);
      const width = drag.width + (drag.x - event.clientX);
      setChatWidth(Math.min(max, Math.max(CHAT_MIN, width)));
    };
    const onUp = () => {
      resizeRef.current = null;
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
  }, []);

  useEffect(() => {
    loadClaims().then(setClaims).catch((e: Error) => setError(e.message));
    loadSampleBpmn()
      .then((xml) => setGraph(parseBpmn(xml)))
      .catch((e: Error) => setError(e.message));
  }, []);

  const flow = useMemo(() => (graph ? toFlow(graph, step) : { nodes: [], edges: [] }), [graph, step]);

  const onFile = (file: File) => {
    file.text().then((xml) => {
      try {
        setGraph(parseBpmn(xml));
        setStep(null);
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    });
  };

  const openSettings = () => {
    setDraft(configRef.current);
    setSettingsOpen(true);
  };

  const saveSettings = () => {
    saveConfig(draft);
    configRef.current = { baseUrl: draft.baseUrl.trim(), token: draft.token.trim() };
    setSettingsOpen(false);
  };

  const showTurn = useCallback((turnId: string, texts: string[]) => {
    const bubbles: ChatMessage[] = (texts.length ? texts : ["Waiting for the agent…"]).map(
      (text, index) => ({
        id: `${turnId}-${index}`,
        role: "agent",
        text,
        turnId,
      })
    );
    setMessages((prev) => [...prev.filter((message) => message.turnId !== turnId), ...bubbles]);
  }, []);

  const sendText = useCallback(
    async (userText: string, claimId: string | null) => {
      const config = configRef.current;
      if (!config.baseUrl || !config.token) {
        setDraft(config);
        setSettingsOpen(true);
        setError("Set the workflow URL and bearer token first.");
        return;
      }
      const turnId = `turn-${Date.now()}`;
      setActiveClaim(claimId);
      setBusy(true);
      setError(null);
      setStep(null);
      setMessages((prev) => [
        ...prev,
        { id: `user-${turnId}`, role: "user", text: userText },
        { id: turnId, role: "agent", text: "Waiting for the agent…", turnId },
      ]);
      try {
        const started = await kickoffMessage(config, userText);
        const conversationId = started.conversation_id || started.trace_id;
        const deadline = Date.now() + POLL_TIMEOUT_MS;
        let answer = "The agent did not finish before the poll timeout.";
        let nextStep: string | null = null;
        let rendered = false;
        while (Date.now() < deadline) {
          await sleep(POLL_MS);
          const polled = await pollEvents(config, conversationId);
          if (polled.responses?.length) {
            showTurn(turnId, polled.responses);
            rendered = true;
          }
          if (!polled.completed) continue;
          const lastResponse = polled.responses?.[polled.responses.length - 1];
          answer = polled.answer || lastResponse || "The agent finished without a reply.";
          nextStep = polled.next_step;
          if (!rendered) showTurn(turnId, [answer]);
          rendered = true;
          break;
        }
        if (!rendered) showTurn(turnId, [answer]);
        setStep(nextStep);
      } catch (e) {
        const text = e instanceof Error ? e.message : String(e);
        setError(text);
        showTurn(turnId, [text]);
      } finally {
        setBusy(false);
      }
    },
    [showTurn]
  );

  const runClaim = useCallback(
    (claimId: string) => {
      void sendText(`process claim ${claimId}`, claimId);
    },
    [sendText]
  );

  const sendComposer = () => {
    const userText = composer.trim();
    if (!userText || busy) return;
    setComposer("");
    void sendText(userText, null);
  };

  return (
    <div className="app">
      <header className="topbar">
        <h1>Adjuster</h1>
        <button className="btn" type="button" onClick={() => fileRef.current?.click()}>
          Load BPMN
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".bpmn,.xml"
          hidden
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) onFile(file);
          }}
        />
        <span className="spacer" />
        <button className="gear" type="button" aria-label="Settings" onClick={openSettings}>
          ⚙
        </button>
      </header>
      {error ? <div className="alert">{error}</div> : null}
      <div className="body" style={{ gridTemplateColumns: `180px minmax(0, 1fr) ${chatWidth}px` }}>
        <aside className="claims">
          <h2>Claims</h2>
          {claims.map((claimId) => (
            <button
              key={claimId}
              type="button"
              className={`claim-btn${activeClaim === claimId ? " is-active" : ""}`}
              disabled={busy}
              onClick={() => void runClaim(claimId)}
            >
              {claimId}
            </button>
          ))}
        </aside>
        <div className="canvas-wrap">
          <ReactFlow
            nodes={flow.nodes}
            edges={flow.edges}
            nodeTypes={nodeTypes}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable={false}
            deleteKeyCode={null}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Background gap={16} />
            <Controls showInteractive={false} />
            <MiniMap
              pannable
              zoomable
              bgColor="#121820"
              maskColor="rgba(15, 20, 25, 0.65)"
              nodeColor="#3b82f6"
            />
          </ReactFlow>
        </div>
        <aside className="chat">
          <div
            className="chat-resizer"
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize chat"
            onPointerDown={(event) => {
              resizeRef.current = { x: event.clientX, width: chatWidth };
            }}
          />
          <h2>Chat</h2>
          <div className="transcript" ref={transcriptRef}>
            {messages.map((message) => (
              <div key={message.id} className={`bubble bubble--${message.role}`}>
                {message.role === "agent" ? (
                  <ReactMarkdown>{message.text}</ReactMarkdown>
                ) : (
                  <p>{message.text}</p>
                )}
              </div>
            ))}
          </div>
          <form
            className="composer"
            onSubmit={(event) => {
              event.preventDefault();
              sendComposer();
            }}
          >
            <textarea
              rows={3}
              value={composer}
              placeholder="Message the agent"
              disabled={busy}
              onChange={(event) => setComposer(event.target.value)}
            />
            <button className="btn btn--accent" type="submit" disabled={busy || !composer.trim()}>
              Send
            </button>
          </form>
        </aside>
      </div>
      {settingsOpen ? (
        <div className="dialog-backdrop" onClick={() => setSettingsOpen(false)}>
          <div
            className="dialog"
            role="dialog"
            aria-label="Workflow settings"
            onClick={(event) => event.stopPropagation()}
          >
            <h2>Workflow</h2>
            <label>
              Agent URL
              <input
                value={draft.baseUrl}
                onChange={(event) => setDraft({ ...draft, baseUrl: event.target.value })}
                placeholder="https://workflow.example"
              />
            </label>
            <label>
              Bearer token
              <input
                type="password"
                value={draft.token}
                onChange={(event) => setDraft({ ...draft, token: event.target.value })}
              />
            </label>
            <div className="dialog-actions">
              <button className="btn" type="button" onClick={() => setSettingsOpen(false)}>
                Cancel
              </button>
              <button className="btn btn--accent" type="button" onClick={saveSettings}>
                Save
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
