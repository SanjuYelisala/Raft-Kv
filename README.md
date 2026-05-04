# Raft-KV

A production-level distributed key-value store built from scratch in Python, implementing the [Raft consensus algorithm](https://raft.github.io/).

## What is Raft?

Raft is a consensus algorithm designed to manage a replicated log across a cluster of nodes. It ensures all nodes agree on the same sequence of operations even in the presence of failures. This project implements the full Raft spec including leader election, log replication, and snapshotting.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Node 1    │────▶│   Node 2    │────▶│   Node 3    │
│  (Leader)   │◀────│  (Follower) │◀────│  (Follower) │
└─────────────┘     └─────────────┘     └─────────────┘
       ▲
       │
┌─────────────┐
│  REST API   │
│  (FastAPI)  │
└─────────────┘
       ▲
       │
┌─────────────┐
│   Client    │
└─────────────┘
```

### File Structure

```
├── RaftNode.py         # Core Raft node — leader election, heartbeats, log replication
├── node.py             # Non-blocking TCP server using selectors
├── message_handler.py  # Routes incoming messages to appropriate handlers
├── election.py         # RequestVote RPC logic
├── messages.py         # Message type definitions
├── connection.py       # TCP connection with message framing
├── log_store.py        # In-memory log with append/get operations
├── kv_store.py         # In-memory key-value store
├── storage.py          # Disk persistence for log, state, and snapshots
├── api.py              # FastAPI REST API
├── client.py           # TCP client for direct node communication
├── Dockerfile          # Docker image definition
├── docker-compose.yml  # Multi-node Docker setup
├── config/
│   └── peers.json      # Cluster node configuration
└── k8s/
    ├── configmap.yaml  # Kubernetes ConfigMap for peers config
    ├── statefulset.yaml # Kubernetes StatefulSet for Raft nodes
    ├── service.yaml    # Kubernetes headless service
    └── nodeport.yaml   # Kubernetes NodePort for external access
```

## Features

### Raft Consensus
- **Leader Election** — randomized election timeouts prevent split votes
- **Log Replication** — leader replicates all writes to followers before committing
- **Heartbeats** — leader sends periodic heartbeats to prevent re-elections
- **Node Catchup** — new or rejoining nodes receive missing log entries
- **Log Consistency Check** — followers reject entries that don't match their log
- **InstallSnapshot RPC** — lagging nodes receive full snapshots instead of log replay
- **Log Compaction** — logs are compacted into snapshots to prevent unbounded growth

### Storage
- **Disk Persistence** — `current_term`, `voted_for`, `commit_index`, and log entries survive restarts
- **Snapshotting** — KV store state is periodically snapshotted and old log entries discarded

### Networking
- **Non-blocking I/O** — uses Python `selectors` for efficient event-driven networking
- **Message Framing** — newline-delimited messages with per-connection buffers
- **Connection Pooling** — reuses TCP connections to peers instead of creating new ones per message
- **Leader Redirect** — followers tell clients who the current leader is

### API
- **REST API** — FastAPI endpoints for CRUD operations
- **API Key Authentication** — requests require `X-Api-Key` header
- **Status Endpoint** — returns node role, term, commit index, and log size
- **TCP Client** — direct low-level client for testing

### Deployment
- **Docker** — containerized with `docker-compose` for local multi-node clusters
- **Kubernetes** — StatefulSet deployment with stable pod identities and headless service DNS

## Getting Started

### Prerequisites

- Python 3.9+
- Docker (optional)
- Kubernetes / kubectl (optional)

### Run Locally

**1. Install dependencies**
```bash
pip install fastapi uvicorn
```

**2. Configure peers**

Edit `config/peers.json`:
```json
{
    "nodes": [
        {"host": "localhost", "port": 5001},
        {"host": "localhost", "port": 5002},
        {"host": "localhost", "port": 5003}
    ]
}
```

**3. Start 3 nodes** (in separate terminals)
```bash
python3 RaftNode.py localhost 5001
python3 RaftNode.py localhost 5002
python3 RaftNode.py localhost 5003
```

**4. Send commands**
```bash
# Set a value
python3 client.py localhost 5001 set foo bar

# Get a value
python3 client.py localhost 5001 get foo

# Delete a value
python3 client.py localhost 5001 del foo

# Check node status
python3 client.py localhost 5001 status
```

### Run with Docker

```bash
docker-compose up --build
```

Then test:
```bash
python3 client.py localhost 5001 set foo bar
python3 client.py localhost 5001 get foo
```

### Run with Kubernetes

```bash
# Build image
docker build -t raft-kv:latest .

# Deploy
kubectl apply -f k8s/

# Check pods
kubectl get pods

# Port-forward to leader
kubectl port-forward pod/raft-2 5001:5001

# Test
python3 client.py localhost 5001 set foo bar
```

## REST API

Start the API server (requires a Raft cluster running):
```bash
uvicorn api:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive API docs.

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/kv/{key}` | Get a value |
| `POST` | `/kv/{key}` | Set a value |
| `DELETE` | `/kv/{key}` | Delete a value |
| `GET` | `/status` | Node status |

All endpoints require `X-Api-Key: secret123` header.

**Example:**
```bash
# Set a value
curl -X POST http://localhost:8000/kv/foo \
  -H "X-Api-Key: secret123" \
  -H "Content-Type: application/json" \
  -d '{"value": "bar"}'

# Get a value
curl http://localhost:8000/kv/foo \
  -H "X-Api-Key: secret123"
```

## How It Works

### Leader Election
Every node starts as a follower with a random election timeout (1-5 seconds). If a follower doesn't receive a heartbeat before the timeout, it becomes a candidate and requests votes from peers. A candidate that receives votes from a majority becomes the leader.

### Log Replication
All writes go to the leader. The leader appends the entry to its log, replicates it to followers via `AppendEntries`, and commits once a majority acknowledges. Committed entries are applied to the KV store and the client receives a response.

### Fault Tolerance
The cluster can tolerate `(n-1)/2` node failures. With 3 nodes, 1 failure is tolerated. If the leader fails, a new election is held within the election timeout window.

### Persistence
On every state change, the node writes `current_term`, `voted_for`, and `commit_index` to disk. Log entries are appended to a JSON file. On restart, the node replays its log to rebuild the KV store state.

## Built With

- **Python 3.9** — core implementation
- **FastAPI** — REST API
- **Docker** — containerization
- **Kubernetes** — orchestration

## What I Learned

This project was built as a learning exercise covering:
- Distributed consensus algorithms (Raft)
- Non-blocking I/O with Python selectors
- TCP message framing and connection pooling
- Log replication and compaction
- Disk persistence and crash recovery
- Docker and Kubernetes deployment

## References

- [In Search of an Understandable Consensus Algorithm (Raft Paper)](https://raft.github.io/raft.pdf)
- [The Raft Consensus Algorithm](https://raft.github.io/)
