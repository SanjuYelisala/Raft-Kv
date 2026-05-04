import { useState, useEffect, useCallback } from "react";
import axios from "axios";

const API_BASE = "http://localhost:8000";
const API_KEY = "secret123";
const NODES = [
  { id: "node1", port: 5001 },
  { id: "node2", port: 5002 },
  { id: "node3", port: 5003 },
];

const headers = { "X-Api-Key": API_KEY };

function parseStatus(raw) {
  try {
    return JSON.parse(raw.replace(/'/g, '"').replace(/None/g, "null").replace(/True/g, "true").replace(/False/g, "false"));
  } catch {
    return null;
  }
}

function NodeCard({ node, status, loading }) {
  const role = status?.role || "unknown";
  const isLeader = role === "leader";
  const isCandidate = role === "candidate";

  return (
    <div style={{
      background: isLeader ? "linear-gradient(135deg, #0f2027, #203a43, #2c5364)" : "#0d1117",
      border: isLeader ? "1px solid #00d4ff" : isCandidate ? "1px solid #ffd700" : "1px solid #21262d",
      borderRadius: "12px",
      padding: "24px",
      position: "relative",
      overflow: "hidden",
      transition: "all 0.3s ease",
      boxShadow: isLeader ? "0 0 30px rgba(0,212,255,0.15)" : "none",
    }}>
      {isLeader && (
        <div style={{
          position: "absolute", top: "12px", right: "12px",
          background: "#00d4ff", color: "#000", fontSize: "10px",
          fontWeight: "700", padding: "3px 8px", borderRadius: "20px",
          letterSpacing: "1px", fontFamily: "monospace"
        }}>LEADER</div>
      )}
      {isCandidate && (
        <div style={{
          position: "absolute", top: "12px", right: "12px",
          background: "#ffd700", color: "#000", fontSize: "10px",
          fontWeight: "700", padding: "3px 8px", borderRadius: "20px",
          letterSpacing: "1px", fontFamily: "monospace"
        }}>VOTING</div>
      )}

      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "20px" }}>
        <div style={{
          width: "10px", height: "10px", borderRadius: "50%",
          background: loading ? "#555" : isLeader ? "#00d4ff" : isCandidate ? "#ffd700" : "#3fb950",
          boxShadow: isLeader ? "0 0 10px #00d4ff" : "none",
          animation: loading ? "none" : "pulse 2s infinite"
        }} />
        <span style={{ color: "#e6edf3", fontFamily: "'JetBrains Mono', monospace", fontSize: "14px", fontWeight: "600" }}>
          {node.id}
        </span>
        <span style={{ color: "#8b949e", fontFamily: "monospace", fontSize: "12px" }}>
          :{node.port}
        </span>
      </div>

      {loading ? (
        <div style={{ color: "#555", fontFamily: "monospace", fontSize: "13px" }}>connecting...</div>
      ) : status ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
          {[
            { label: "ROLE", value: status.role },
            { label: "TERM", value: status.term },
            { label: "COMMIT", value: status.commit_index },
            { label: "LOG SIZE", value: status.log_size },
            { label: "SNAPSHOT", value: status.snapshot_index },
            { label: "LEADER", value: status.leader ? status.leader.split(":")[0] : "—" },
          ].map(({ label, value }) => (
            <div key={label}>
              <div style={{ color: "#8b949e", fontSize: "10px", fontFamily: "monospace", letterSpacing: "1px", marginBottom: "2px" }}>{label}</div>
              <div style={{ color: isLeader ? "#00d4ff" : "#e6edf3", fontSize: "14px", fontFamily: "'JetBrains Mono', monospace", fontWeight: "500" }}>
                {value ?? "—"}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ color: "#f85149", fontFamily: "monospace", fontSize: "13px" }}>offline</div>
      )}
    </div>
  );
}

function KVPanel({ onNotify }) {
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const inputStyle = {
    background: "#0d1117", border: "1px solid #21262d", borderRadius: "8px",
    padding: "10px 14px", color: "#e6edf3", fontFamily: "'JetBrains Mono', monospace",
    fontSize: "13px", outline: "none", width: "100%", boxSizing: "border-box",
    transition: "border-color 0.2s"
  };

  const btnStyle = (color) => ({
    background: "transparent", border: `1px solid ${color}`, borderRadius: "8px",
    padding: "10px 20px", color, fontFamily: "monospace", fontSize: "13px",
    cursor: "pointer", transition: "all 0.2s", letterSpacing: "0.5px", fontWeight: "600"
  });

  const doGet = async () => {
    if (!key) return;
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/kv/${key}`, { headers });
      setResult({ type: "success", msg: `${key} = ${res.data.value ?? "NOT FOUND"}` });
    } catch (e) {
      setResult({ type: "error", msg: e.response?.data?.detail || "error" });
    }
    setLoading(false);
  };

  const doSet = async () => {
    if (!key || !value) return;
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/kv/${key}`, { value }, { headers });
      setResult({ type: "success", msg: res.data.response });
      onNotify(`✓ set ${key} = ${value}`);
    } catch (e) {
      const detail = e.response?.data?.detail || e.message;
      setResult({ type: "error", msg: detail });
    }
    setLoading(false);
  };

  const doDelete = async () => {
    if (!key) return;
    setLoading(true);
    try {
      const res = await axios.delete(`${API_BASE}/kv/${key}`, { headers });
      setResult({ type: "success", msg: res.data.response });
      onNotify(`✓ deleted ${key}`);
    } catch (e) {
      setResult({ type: "error", msg: e.response?.data?.detail || "error" });
    }
    setLoading(false);
  };

  return (
    <div style={{
      background: "#0d1117", border: "1px solid #21262d", borderRadius: "12px", padding: "24px"
    }}>
      <div style={{ color: "#8b949e", fontSize: "11px", fontFamily: "monospace", letterSpacing: "2px", marginBottom: "20px" }}>
        KV OPERATIONS
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        <input
          style={inputStyle} placeholder="key" value={key}
          onChange={e => setKey(e.target.value)}
          onFocus={e => e.target.style.borderColor = "#00d4ff"}
          onBlur={e => e.target.style.borderColor = "#21262d"}
        />
        <input
          style={inputStyle} placeholder="value (for SET)" value={value}
          onChange={e => setValue(e.target.value)}
          onFocus={e => e.target.style.borderColor = "#00d4ff"}
          onBlur={e => e.target.style.borderColor = "#21262d"}
        />

        <div style={{ display: "flex", gap: "8px" }}>
          <button style={btnStyle("#3fb950")} onClick={doSet}
            onMouseEnter={e => { e.target.style.background = "#3fb950"; e.target.style.color = "#000"; }}
            onMouseLeave={e => { e.target.style.background = "transparent"; e.target.style.color = "#3fb950"; }}>
            SET
          </button>
          <button style={btnStyle("#00d4ff")} onClick={doGet}
            onMouseEnter={e => { e.target.style.background = "#00d4ff"; e.target.style.color = "#000"; }}
            onMouseLeave={e => { e.target.style.background = "transparent"; e.target.style.color = "#00d4ff"; }}>
            GET
          </button>
          <button style={btnStyle("#f85149")} onClick={doDelete}
            onMouseEnter={e => { e.target.style.background = "#f85149"; e.target.style.color = "#000"; }}
            onMouseLeave={e => { e.target.style.background = "transparent"; e.target.style.color = "#f85149"; }}>
            DEL
          </button>
        </div>

        {loading && <div style={{ color: "#8b949e", fontFamily: "monospace", fontSize: "13px" }}>executing...</div>}

        {result && (
          <div style={{
            padding: "12px", borderRadius: "8px", fontFamily: "'JetBrains Mono', monospace", fontSize: "13px",
            background: result.type === "success" ? "rgba(63,185,80,0.1)" : "rgba(248,81,73,0.1)",
            border: `1px solid ${result.type === "success" ? "#3fb950" : "#f85149"}`,
            color: result.type === "success" ? "#3fb950" : "#f85149",
          }}>
            {result.msg}
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [statuses, setStatuses] = useState({});
  const [loading, setLoading] = useState({});
  const [notifications, setNotifications] = useState([]);
  const [tick, setTick] = useState(0);

  const fetchStatus = useCallback(async () => {
    for (const node of NODES) {
      setLoading(prev => ({ ...prev, [node.id]: true }));
      try {
        const res = await axios.get(`${API_BASE}/status?node_port=${node.port}`, { headers, timeout: 2000 });
        const parsed = parseStatus(res.data.status);
        setStatuses(prev => ({ ...prev, [node.id]: parsed }));
      } catch {
        setStatuses(prev => ({ ...prev, [node.id]: null }));
      }
      setLoading(prev => ({ ...prev, [node.id]: false }));
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(() => {
      setTick(t => t + 1);
      fetchStatus();
    }, 3000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const addNotification = (msg) => {
    const id = Date.now();
    setNotifications(prev => [...prev, { id, msg }]);
    setTimeout(() => setNotifications(prev => prev.filter(n => n.id !== id)), 3000);
  };

  const leader = Object.entries(statuses).find(([, s]) => s?.role === "leader")?.[0];

  return (
    <div style={{
      minHeight: "100vh", background: "#010409", color: "#e6edf3",
      fontFamily: "'JetBrains Mono', monospace", padding: "40px",
      backgroundImage: "radial-gradient(ellipse at 20% 50%, rgba(0,212,255,0.03) 0%, transparent 50%), radial-gradient(ellipse at 80% 20%, rgba(63,185,80,0.03) 0%, transparent 50%)"
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        * { margin: 0; padding: 0; box-sizing: border-box; }
      `}</style>

      {/* Notifications */}
      <div style={{ position: "fixed", top: "20px", right: "20px", zIndex: 1000, display: "flex", flexDirection: "column", gap: "8px" }}>
        {notifications.map(n => (
          <div key={n.id} style={{
            background: "#0d1117", border: "1px solid #3fb950", borderRadius: "8px",
            padding: "10px 16px", color: "#3fb950", fontSize: "13px",
            animation: "slideIn 0.3s ease"
          }}>{n.msg}</div>
        ))}
      </div>

      {/* Header */}
      <div style={{ marginBottom: "40px", borderBottom: "1px solid #21262d", paddingBottom: "24px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <h1 style={{ fontSize: "24px", fontWeight: "700", color: "#e6edf3", letterSpacing: "-0.5px" }}>
              RAFT<span style={{ color: "#00d4ff" }}>·</span>KV
            </h1>
            <p style={{ color: "#8b949e", fontSize: "12px", marginTop: "4px", letterSpacing: "1px" }}>
              DISTRIBUTED KEY-VALUE STORE
            </p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            {leader && (
              <div style={{ color: "#8b949e", fontSize: "12px" }}>
                leader: <span style={{ color: "#00d4ff" }}>{leader}</span>
              </div>
            )}
            <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "#8b949e", fontSize: "12px" }}>
              <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#3fb950", animation: "pulse 2s infinite" }} />
              auto-refresh 3s
            </div>
          </div>
        </div>
      </div>

      {/* Cluster Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px", marginBottom: "32px" }}>
        {[
          { label: "NODES ONLINE", value: Object.values(statuses).filter(Boolean).length + " / " + NODES.length },
          { label: "CURRENT TERM", value: Math.max(...Object.values(statuses).map(s => s?.term || 0)) || "—" },
          { label: "COMMIT INDEX", value: Math.max(...Object.values(statuses).map(s => s?.commit_index || 0)) || "—" },
        ].map(({ label, value }) => (
          <div key={label} style={{
            background: "#0d1117", border: "1px solid #21262d", borderRadius: "12px",
            padding: "20px 24px"
          }}>
            <div style={{ color: "#8b949e", fontSize: "10px", letterSpacing: "2px", marginBottom: "8px" }}>{label}</div>
            <div style={{ color: "#e6edf3", fontSize: "28px", fontWeight: "700" }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Main Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 320px", gap: "16px" }}>
        {NODES.map(node => (
          <NodeCard
            key={node.id}
            node={node}
            status={statuses[node.id]}
            loading={loading[node.id]}
          />
        ))}
        <KVPanel onNotify={addNotification} />
      </div>
    </div>
  );
}
