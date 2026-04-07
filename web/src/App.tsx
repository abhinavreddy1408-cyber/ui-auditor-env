import { useEffect, useMemo, useState } from "react";
import {
  getState,
  getTasks,
  resetEnv,
  runAgent,
  stepEnv,
} from "./lib/api";
import type { ActionPayload, Observation, StepLog, TaskMeta } from "./types";

type ViewMode = "tree" | "json";

const emptyAction: ActionPayload = {
  action_type: "update_attribute",
  node_id: "",
  attr_name: "",
  new_value: "",
  css_property: "",
  new_hex_code: "",
  new_child_order: [],
};

const prettyJson = (value: unknown) => JSON.stringify(value, null, 2);

function DomNode({ node }: { node: Record<string, any> }) {
  return (
    <div className="dom-node">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
        <strong>
          {node.type} <span className="muted">#{node.id}</span>
        </strong>
        {node.content && <span className="muted">{node.content}</span>}
      </div>
      {node.css && (
        <div className="muted" style={{ fontSize: 12 }}>
          css: {Object.entries(node.css).map(([k, v]) => `${k}: ${v}`).join(", ")}
        </div>
      )}
      {node.children && node.children.length > 0 && (
        <div className="dom-children">
          {node.children.map((child: any) => (
            <DomNode key={child.id} node={child} />
          ))}
        </div>
      )}
    </div>
  );
}

const ScoreChip = ({ score }: { score: number }) => (
  <span className="score-chip" aria-label="current-score">
    <span
      style={{
        width: 10,
        height: 10,
        borderRadius: 999,
        background: score >= 1 ? "var(--success)" : "var(--gold)",
        display: "inline-block",
      }}
    />
    Score {score.toFixed(2)}
  </span>
);

function App() {
  const [tasks, setTasks] = useState<TaskMeta[]>([]);
  const [selectedTask, setSelectedTask] = useState("easy");
  const [observation, setObservation] = useState<Observation | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("tree");
  const [action, setAction] = useState<ActionPayload>(emptyAction);
  const [childOrderInput, setChildOrderInput] = useState("");
  const [timeline, setTimeline] = useState<StepLog[]>([]);
  const [rewardHistory, setRewardHistory] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [agentRunning, setAgentRunning] = useState(false);
  const [model, setModel] = useState("nvidia/nemotron-3-super-120b-a12b");
  const [baseUrl, setBaseUrl] = useState("https://integrate.api.nvidia.com/v1");
  const [apiKey, setApiKey] = useState("");
  const [booted, setBooted] = useState(false);

  const lastAction = timeline.length ? timeline[timeline.length - 1].action : null;
  const curlSnippet = useMemo(() => {
    if (!lastAction) return "";
    const payload = JSON.stringify({ action: lastAction, task_difficulty: selectedTask }, null, 2);
    return `curl -X POST http://localhost:7860/ui/step \\\n  -H 'Content-Type: application/json' \\\n  -d '${payload.replace(/'/g, "'\"'\"'")}'`;
  }, [lastAction, selectedTask]);

  const refreshState = async () => {
    const current = await getState();
    setObservation(current);
    setRewardHistory([current.current_score]);
  };

  useEffect(() => {
    let cancelled = false;
    const bootstrap = async () => {
      try {
        setLoading(true);
        setError(null);
        if (!booted) {
          const fetched = await getTasks();
          if (!cancelled) {
            setTasks(fetched);
            setBooted(true);
          }
        }
        const obs = await resetEnv(selectedTask);
        if (!cancelled) {
          setObservation(obs);
          setRewardHistory([obs.current_score]);
          setTimeline([]);
          setChildOrderInput("");
          setAction(emptyAction);
        }
      } catch (err: any) {
        if (!cancelled) setError(err.message || "Failed to load tasks");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    bootstrap();
    return () => {
      cancelled = true;
    };
  }, [selectedTask, booted]);

  const handleReset = async () => {
    try {
      setLoading(true);
      setError(null);
      const obs = await resetEnv(selectedTask);
      setObservation(obs);
      setRewardHistory([obs.current_score]);
      setTimeline([]);
      setChildOrderInput("");
      setAction(emptyAction);
    } catch (err: any) {
      setError(err.message || "Failed to reset");
    } finally {
      setLoading(false);
    }
  };

  const handleStep = async () => {
    if (!action.node_id) {
      setError("Node ID is required.");
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const payload: ActionPayload = {
        ...action,
        new_child_order:
          action.action_type === "reorder_nodes"
            ? childOrderInput
                .split(",")
                .map((c) => c.trim())
                .filter(Boolean)
            : [],
      };
      const obs = await stepEnv(payload, selectedTask);
      const newLog: StepLog = {
        step: timeline.length + 1,
        action: payload,
        score: obs.current_score,
        feedback: obs.feedback,
      };
      setTimeline((prev) => [...prev, newLog]);
      setRewardHistory((prev) => [...prev, obs.current_score]);
      setObservation(obs);
    } catch (err: any) {
      setError(err.message || "Failed to step");
    } finally {
      setLoading(false);
    }
  };

  const handleRunAgent = async () => {
    try {
      setAgentRunning(true);
      setError(null);
      const result = await runAgent({
        task_difficulty: selectedTask,
        model,
        base_url: baseUrl,
        api_key: apiKey || undefined,
        max_steps: 8,
      });
      setTimeline(result.steps);
      if (result.steps.length) {
        setRewardHistory(result.steps.map((s) => s.score));
        const last = result.steps[result.steps.length - 1];
        setObservation({
          ...(observation as Observation),
          current_score: last.score,
          feedback: last.feedback,
          done: last.score >= 1,
        });
      } else {
        await refreshState();
      }
    } catch (err: any) {
      setError(err.message || "Agent run failed");
    } finally {
      setAgentRunning(false);
    }
  };

  const renderDom = () => {
    if (!observation) return null;
    if (viewMode === "json") {
      return <pre className="code">{prettyJson(observation.dom_state)}</pre>;
    }
    return <DomNode node={observation.dom_state} />;
  };

  return (
    <div className="app-shell">
      <div className="panel stack">
        <div className="stack">
          <div>
            <p className="muted" style={{ margin: 0 }}>
              UI Accessibility Auditor
            </p>
            <h2 className="title">Control Rail</h2>
          </div>
          <ScoreChip score={observation?.current_score || 0} />
        </div>
        <div className="divider" />

        <div className="stack">
          <p className="muted">Task</p>
          <div className="chips">
            {tasks.map((task) => (
              <button
                key={task.id}
                className={`chip ${selectedTask === task.id ? "active" : ""}`}
                onClick={() => setSelectedTask(task.id)}
              >
                {task.label}
              </button>
            ))}
          </div>
          <p className="muted" style={{ marginTop: -6 }}>
            {tasks.find((t) => t.id === selectedTask)?.description}
          </p>
        </div>

        <div className="divider" />
        <div className="stack">
          <div className="grid-two">
            <div className="field">
              <label>Model</label>
              <input
                className="input"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="gpt-4o-mini"
              />
            </div>
            <div className="field">
              <label>Base URL</label>
              <input
                className="input"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
              />
            </div>
          </div>
          <div className="field">
            <label>API Key (not stored)</label>
            <input
              className="input"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              type="password"
            />
          </div>
        </div>

        <div className="actions-row">
          <button className="btn" onClick={handleReset} disabled={loading}>
            Reset
          </button>
          <button
            className="btn secondary"
            onClick={handleRunAgent}
            disabled={agentRunning || loading}
          >
            {agentRunning ? "Running..." : "Run Agent"}
          </button>
        </div>
        {error && <p className="danger">{error}</p>}
      </div>

      <div className="panel stack">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <p className="muted" style={{ margin: 0 }}>
              DOM Visualizer
            </p>
            <h2 className="title">Live View</h2>
          </div>
          <div className="toggle">
            <button
              className={viewMode === "tree" ? "active" : ""}
              onClick={() => setViewMode("tree")}
            >
              Tree
            </button>
            <button
              className={viewMode === "json" ? "active" : ""}
              onClick={() => setViewMode("json")}
            >
              JSON
            </button>
          </div>
        </div>
        <div className="dom-container">{renderDom()}</div>
        <div className="reward-bar" aria-label="reward-bar">
          <div style={{ width: `${(observation?.current_score || 0) * 100}%` }} />
        </div>
      </div>

      <div className="panel stack">
        <div>
          <p className="muted" style={{ margin: 0 }}>
            Actions
          </p>
          <h2 className="title">Manual Builder</h2>
        </div>

        <div className="field">
          <label>Action Type</label>
          <select
            className="select"
            value={action.action_type}
            onChange={(e) =>
              setAction((prev) => ({ ...prev, action_type: e.target.value as ActionPayload["action_type"] }))
            }
          >
            <option value="update_attribute">update_attribute</option>
            <option value="modify_css">modify_css</option>
            <option value="reorder_nodes">reorder_nodes</option>
          </select>
        </div>

        <div className="field">
          <label>node_id</label>
          <input
            className="input"
            value={action.node_id}
            onChange={(e) => setAction((prev) => ({ ...prev, node_id: e.target.value }))}
            placeholder="hero-img, upgrade-btn..."
          />
        </div>

        {action.action_type === "update_attribute" && (
          <div className="grid-two">
            <div className="field">
              <label>attr_name</label>
              <input
                className="input"
                value={action.attr_name || ""}
                onChange={(e) => setAction((prev) => ({ ...prev, attr_name: e.target.value }))}
                placeholder="alt, type..."
              />
            </div>
            <div className="field">
              <label>new_value</label>
              <input
                className="input"
                value={action.new_value || ""}
                onChange={(e) => setAction((prev) => ({ ...prev, new_value: e.target.value }))}
                placeholder="A premium dashboard..."
              />
            </div>
          </div>
        )}

        {action.action_type === "modify_css" && (
          <div className="grid-two">
            <div className="field">
              <label>css_property</label>
              <input
                className="input"
                value={action.css_property || ""}
                onChange={(e) => setAction((prev) => ({ ...prev, css_property: e.target.value }))}
                placeholder="color, border..."
              />
            </div>
            <div className="field">
              <label>new_hex_code</label>
              <input
                className="input"
                value={action.new_hex_code || ""}
                onChange={(e) => setAction((prev) => ({ ...prev, new_hex_code: e.target.value }))}
                placeholder="#50C878"
              />
            </div>
          </div>
        )}

        {action.action_type === "reorder_nodes" && (
          <div className="field">
            <label>new_child_order (comma separated)</label>
            <textarea
              className="textarea"
              value={childOrderInput}
              onChange={(e) => setChildOrderInput(e.target.value)}
              placeholder="main-title, subtitle, sub-subtitle"
            />
          </div>
        )}

        <div className="actions-row">
          <button className="btn" onClick={handleStep} disabled={loading}>
            Send Step
          </button>
          <button className="btn secondary" onClick={handleReset} disabled={loading}>
            Reset Task
          </button>
        </div>

        <div className="divider" />
        <p className="muted">Step Timeline</p>
        <div className="timeline">
          {timeline.length === 0 && <p className="muted">No steps yet.</p>}
          {timeline.map((item) => (
            <div key={item.step} className="timeline-card">
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                <div className="badge">Step {item.step}</div>
                <div className="badge" style={{ borderColor: "rgba(80,200,120,0.5)" }}>
                  Score {item.score.toFixed(2)}
                </div>
              </div>
              <p style={{ margin: "8px 0 4px" }} className="muted">
                {item.feedback}
              </p>
              <pre className="code">{prettyJson(item.action)}</pre>
            </div>
          ))}
        </div>

        <div className="divider" />
        <p className="muted">Last Action (cURL)</p>
        <pre className="code" style={{ whiteSpace: "pre-wrap" }}>
          {curlSnippet || "Run an action to see the snippet."}
        </pre>

        <div className="divider" />
        <p className="muted">Reward Trend</p>
        <div className="actions-row" style={{ gap: 6 }}>
          {rewardHistory.map((score, idx) => (
            <div key={idx} className="pill">
              #{idx + 1} • {score.toFixed(2)}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default App;
