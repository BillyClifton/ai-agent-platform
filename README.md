# AI Agent Platform

A production-ready AI Agent Platform built with a **MCP Gateway**, **Temporal** workflow orchestration, **FastAPI + FastMCP**, **PostgreSQL**, a **Python Agent SDK**, and a **TailwindCSS HTML UI** — deployable on **Kubernetes**.

```
┌──────────────────────────────────────────────────────────────────────┐
│                         AI Agent Platform                            │
│                                                                      │
│   Browser / Claude                                                   │
│       │                                                              │
│       ▼                                                              │
│  ┌─────────────────────────────────────────────────────────┐        │
│  │              MCP Gateway  (FastAPI + FastMCP)            │        │
│  │   /api/v1/*  REST API for UI                             │        │
│  │   /mcp/*     MCP SSE endpoint for AI clients             │        │
│  │   /          TailwindCSS HTML UI                         │        │
│  └──────────────┬──────────────────────────────────────────┘        │
│                 │  start_workflow()                                   │
│                 ▼                                                    │
│         ┌──────────────┐      activities      ┌───────────────┐    │
│         │   Temporal    │ ──────────────────── │    Worker     │    │
│         │   Server      │                      │  (Python SDK) │    │
│         └──────────────┘                       └───────────────┘    │
│                 │                                      │             │
│                 ▼                                      ▼             │
│         ┌──────────────────────────────────────────────────────┐   │
│         │                    PostgreSQL                          │   │
│         └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

## Stack

| Layer | Technology |
|-------|-----------|
| HTTP API + MCP Server | FastAPI + FastMCP |
| Workflow Orchestration | Temporal |
| Database | PostgreSQL 15 |
| Agent SDK | Python 3.12 |
| UI | HTML + TailwindCSS + Vanilla JS |
| Container Runtime | Docker / Kubernetes |

---

## Quick Start (Docker Compose)

### Prerequisites

- Docker & Docker Compose v2+

### 1 – Clone and start

```bash
git clone https://github.com/BillyClifton/ai-agent-platform.git
cd ai-agent-platform
docker compose up --build
```

### 2 – Open the UI

Navigate to **http://localhost:8000** in your browser.

### 3 – Explore

| Service | URL |
|---------|-----|
| Platform UI | http://localhost:8000 |
| REST API (Swagger) | http://localhost:8000/api/docs |
| MCP SSE endpoint | http://localhost:8000/mcp/sse |
| Temporal UI | http://localhost:8088 |

---

## Directory Structure

```
ai-agent-platform/
├── docker-compose.yml           # Local dev stack
├── migrations/
│   └── 001_initial.sql          # PostgreSQL schema + seed data
├── config/
│   └── temporal/                # Temporal dynamic config
│
├── gateway/                     # MCP Gateway service
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Pydantic Settings
│   ├── database.py              # Async SQLAlchemy engine
│   ├── models.py                # ORM models (Agent, Task, ToolCall)
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── mcp_server.py            # FastMCP tools (list_agents, run_agent…)
│   ├── temporal_client.py       # Temporal workflow starter
│   └── routers/
│       ├── agents.py            # /api/v1/agents CRUD
│       └── tasks.py             # /api/v1/tasks CRUD + stats
│
├── workers/                     # Temporal worker process
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                  # Worker entry point
│   ├── workflows.py             # AgentExecutionWorkflow
│   └── activities.py            # execute_agent, update_task_status
│
├── agent_sdk/                   # Python SDK for building agents
│   ├── __init__.py
│   ├── agent.py                 # BaseAgent class
│   ├── tool.py                  # @tool decorator
│   ├── client.py                # GatewayClient (httpx)
│   └── types.py                 # AgentConfig, TaskResult, ToolDefinition
│
├── ui/                          # Static HTML/JS front end
│   ├── index.html               # Single-page app shell (TailwindCSS)
│   └── static/
│       └── app.js               # Vanilla JS SPA logic
│
└── k8s/                         # Kubernetes manifests
    ├── namespace.yaml
    ├── configmap.yaml
    ├── secret.yaml
    ├── gateway/
    │   ├── deployment.yaml
    │   └── service.yaml         # ClusterIP + Ingress
    ├── worker/
    │   └── deployment.yaml
    ├── postgres/
    │   ├── statefulset.yaml
    │   ├── service.yaml
    │   └── pvc.yaml
    └── temporal/
        └── deployment.yaml
```

---

## MCP Gateway

The gateway exposes these **MCP tools** (available to any MCP-compatible AI client):

| Tool | Description |
|------|-------------|
| `list_agents()` | Return all registered agents |
| `run_agent(agent_name, input_text)` | Submit a task to an agent |
| `get_task_status(task_id)` | Poll task status |
| `get_task_result(task_id)` | Retrieve output + tool calls |
| `list_tools()` | List all available MCP tools |

### Connect Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ai-agent-platform": {
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```

---

## Agent SDK

Build your own agent by subclassing `BaseAgent`:

```python
from agent_sdk import BaseAgent, tool

class MyResearchAgent(BaseAgent):
    name = "my-research-agent"
    description = "Researches topics and produces concise summaries."

    @tool(description="Search the internet for a query")
    async def web_search(self, query: str) -> str:
        # integrate with a real search API
        return f"Search results for: {query}"

    @tool(description="Summarise long text")
    async def summarise(self, text: str, max_words: int = 200) -> str:
        # integrate with your LLM of choice
        return text[:max_words * 6]  # placeholder

# Register and run a task
import asyncio

async def main():
    agent = MyResearchAgent(gateway_url="http://localhost:8000")
    await agent.register()
    result = await agent.run_task("Explain quantum computing")
    print(result.output)

asyncio.run(main())
```

---

## REST API

Full OpenAPI docs available at `GET /api/docs`.

### Key endpoints

```
GET  /api/v1/agents                List agents
POST /api/v1/agents                Register an agent
GET  /api/v1/agents/{id}           Get agent
PATCH /api/v1/agents/{id}          Update agent
DELETE /api/v1/agents/{id}         Delete agent

GET  /api/v1/tasks                 List tasks  (?status_filter=running)
POST /api/v1/tasks                 Create & start task
GET  /api/v1/tasks/stats           Platform statistics
GET  /api/v1/tasks/{id}            Task detail + tool calls
DELETE /api/v1/tasks/{id}          Delete task
```

---

## Kubernetes Deployment

```bash
# Create namespace + resources
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml

# Edit k8s/secret.yaml with your real credentials, then:
kubectl apply -f k8s/secret.yaml

kubectl apply -f k8s/postgres/
kubectl apply -f k8s/temporal/
kubectl apply -f k8s/gateway/
kubectl apply -f k8s/worker/
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | *(required)* | Async PostgreSQL DSN – set via env or `.env` file |
| `TEMPORAL_HOST` | `localhost:7233` | Temporal frontend address |
| `TEMPORAL_NAMESPACE` | `default` | Temporal namespace |
| `TEMPORAL_TASK_QUEUE` | `agent-tasks` | Temporal task queue name |
| `LOG_LEVEL` | `info` | Python log level |
| `CORS_ORIGINS` | `["http://localhost:3000","http://localhost:8000"]` | JSON-encoded CORS origins |

---

## Development

```bash
# Install gateway deps
cd gateway && pip install -r requirements.txt

# Run gateway (requires running Postgres + Temporal)
uvicorn gateway.main:app --reload --port 8000

# Run worker
python -m workers.main
```

