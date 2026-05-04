# Raft-KV

A production-level distributed key-value store built from scratch in Python, implementing the [Raft consensus algorithm](https://raft.github.io/raft.pdf). Includes a React dashboard, REST API, Docker support, and Kubernetes deployment.

![Python](https://img.shields.io/badge/Python-3.9-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![React](https://img.shields.io/badge/React-18-61dafb)
![Docker](https://img.shields.io/badge/Docker-ready-2496ed)
![Kubernetes](https://img.shields.io/badge/Kubernetes-ready-326ce5)

---

## What is Raft?

Raft is a consensus algorithm that ensures a cluster of nodes agrees on the same sequence of operations even when nodes fail. This project implements the full Raft specification from scratch — no consensus libraries used.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              React Dashboard                │
│         (localhost:5173)                    │
└─────────────────┬───────────────────────────┘
                  │ HTTP
┌─────────────────▼───────────────────────────┐
│           FastAPI REST API                  │
│         (localhost:8000)                    │
└──────┬──────────┬──────────┬────────────────┘
       │ TCP      │ TCP      │ TCP
┌──────▼──┐  ┌───▼─────┐  ┌─▼───────┐
│ Node 1  │  │ Node 2  │  │ Node 3  │
│ :5001   │◄─►│ :5002   │◄─►│ :5003   │
│(Leader) │  │(Follower│  │(Follower│
└─────────┘  └─────────┘  └─────────┘
```

### File Structure

```
├── RaftNode.py           # Core Raft node (election, replication, heartbeats)
├── node.py               # Non-blocking TCP server using selectors
├── message_handler.py    # Routes Raft and client messages
├── election.py           # RequestVote RPC
├── messages.py           # Message builders (AppendEntries, RequestVote, etc.)
├── connection.py         # TCP connection with newline message framing
├── log_store.py          # In-memory replicated log
├── kv_store.py           # In-memory key-value store
├── storage.py            # Disk persistence (log, state, snapshots)
├── api.py                # FastAPI REST API with authentication
├── client.py             # TCP CLI client
├── Dockerfile            # Docker image
├── docker-compose.yml    # Multi-node Docker setup
├── config/
│   ├── peers.json        # Local cluster config
│   └── peers-docker.json # Docker cluster config
├── k8s/
│   ├── configmap.yaml    # Kubernetes ConfigMap
│   ├── statefulset.yaml  # Kubernetes StatefulSet
│   ├── service.yaml      # Kubernetes headless service
│   └── nodeport.yaml     # Kubernetes external access
└── raft-dashboard/       # React dashboard (Vite)
    └── src/App.jsx       # Dashboard UI
```

---

## Features

### Raft Consensus (Full Implementation)
- **Leader Election** — randomized timeouts, majority voting
- **Log Replication** — leader replicates all writes before committing
- **Heartbeats** — prevent unnecessary re-elections
- **Node Catchup** — lagging nodes receive missing log entries on rejoin
- **Log Consistency Check** — followers reject inconsistent entries
- **InstallSnapshot RPC** — nodes too far behind receive full state snapshots
- **Log Compaction** — periodic snapshots prevent unbounded log growth
- **Disk Persistence** — term, voted_for, commit_index, log, and snapshots survive restarts
- **Graceful Shutdown** — flushes state to disk on Ctrl+C

### Networking
- **Non-blocking I/O** — Python `selectors` for event-driven networking
- **Message Framing** — newline-delimited messages with per-connection byte buffers
- **Connection Pooling** — reuses TCP connections to peers
- **Leader Redirect** — followers tell clients who the leader is

### API & Dashboard
- **REST API** — FastAPI with automatic `/docs` (Swagger UI)
- **API Key Authentication** — `X-Api-Key` header required
- **Auto Leader Discovery** — API finds the current leader automatically
- **React Dashboard** — live cluster visualization with KV operations
- **Status Endpoint** — per-node role, term, commit index, log size

### Deployment
- **Docker** — `docker-compose up` starts a full 3-node cluster
- **Kubernetes** — StatefulSet with stable DNS names (`raft-0.raft`, etc.)

---

## Getting Started

### Prerequisites
- Python 3.9+
- Node.js 18+ (for dashboard)
- Docker (optional)
- kubectl (optional)

### Run Locally

**1. Install Python dependencies**
```bash
pip install fastapi uvicorn
```

**2. Start 3 Raft nodes**
```bash
python3 RaftNode.py localhost 5001 &
python3 RaftNode.py localhost 5002 &
python3 RaftNode.py localhost 5003 &
```

**3. Start the REST API**
```bash
uvicorn api:app --reload --port 8000
```

**4. Start the React dashboard**
```bash
cd raft-dashboard
npm install
npm run dev
```

Open `http://localhost:5173` to see the dashboard.

**5. Use the CLI client**
```bash
python3 client.py localhost 5001 set foo bar
python3 client.py localhost 5001 get foo
python3 client.py localhost 5001 del foo
python3 client.py localhost 5001 status
```

---

### Run with Docker

```bash
docker-compose up --build
```

Test:
```bash
python3 client.py localhost 5001 set foo bar
python3 client.py localhost 5001 get foo
```

---

### Run with Kubernetes

```bash
# Build image
docker build -t raft-kv:latest .

# Deploy cluster
kubectl apply -f k8s/

# Check pods
kubectl get pods

# Find the leader and port-forward
kubectl logs raft-0 | grep LEADER
kubectl port-forward pod/raft-2 5001:5001

# Test
python3 client.py localhost 5001 set foo bar
```

---

## REST API

Base URL: `http://localhost:8000`

All endpoints require header: `X-Api-Key: secret123`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/kv/{key}` | Get a value |
| `POST` | `/kv/{key}` | Set a value |
| `DELETE` | `/kv/{key}` | Delete a value |
| `GET` | `/status?node_port=5001` | Node status |

**Interactive docs:** `http://localhost:8000/docs`

**Examples:**
```bash
# Set
curl -X POST http://localhost:8000/kv/foo \
  -H "X-Api-Key: secret123" \
  -H "Content-Type: application/json" \
  -d '{"value": "bar"}'

# Get
curl http://localhost:8000/kv/foo \
  -H "X-Api-Key: secret123"

# Status
curl "http://localhost:8000/status?node_port=5001" \
  -H "X-Api-Key: secret123"
```

---

## How Raft Works

### Leader Election
Every node starts as a **follower** with a random election timeout (1–5s). If no heartbeat arrives before the timeout, the node becomes a **candidate**, increments its term, votes for itself, and requests votes from peers. First candidate to win a majority becomes **leader**.

### Log Replication
All writes go to the leader. The leader:
1. Appends the entry to its local log
2. Replicates to all followers via `AppendEntries`
3. Commits once a majority acknowledges
4. Applies to the KV store and responds to the client

Followers that lag behind receive missing entries on the next heartbeat. Nodes too far behind receive a full `InstallSnapshot`.

### Fault Tolerance
With 3 nodes, the cluster tolerates 1 failure. If the leader fails, a new election completes within the election timeout window.

### Persistence
On every state change, the node writes to disk:
- `data/{node}_state.json` — `current_term`, `voted_for`, `commit_index`
- `data/{node}_log.json` — log entries
- `snapshots/{node}_file.json` — KV store snapshot

On restart, the node loads this state and replays any committed log entries not yet in the snapshot.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Consensus | Python (from scratch) |
| Networking | Python `socket` + `selectors` |
| API | FastAPI + Uvicorn |
| Dashboard | React + Vite + Axios |
| Containerization | Docker + docker-compose |
| Orchestration | Kubernetes (StatefulSet) |

---

## References

- [In Search of an Understandable Consensus Algorithm](https://raft.github.io/raft.pdf) — original Raft paper
- [The Raft Consensus Algorithm](https://raft.github.io/) — visual explanation
