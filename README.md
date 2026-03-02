# Game Server Edge Platform (Prototype)

A distributed game server management platform. Volunteers (Edge Nodes) contribute compute resources, and the Center schedules game servers on them with support for data persistence and migration.

## Architecture

*   **Center (`center/`)**: Brain of the system.
    *   FastAPI backend.
    *   Manages Node Registration, Heartbeats, and Task Queue.
    *   API to Deploy instances and monitor status.
*   **Edge Agent (`edge-agent/`)**: Daemon running on volunteer nodes.
    *   Registers with Center.
    *   Executes Docker containers for game servers.
    *   Syncs game saves from "Remote Storage" (simulated via `local://tmp/game_saves/`).

## Project Structure

```
.
├── center/
│   └── app/
│       └── main.py  # Central Control Plane Access
├── edge-agent/
│   └── agent.py     # Worker Node Logic
└── requirements.txt
```

## Setup & Running

1.  **Install Dependencies**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Start Center**:
    ```bash
    uvicorn center.app.main:app --host 0.0.0.0 --port 8000 --reload
    ```

3.  **Start Edge Agent** (Option A: Python):
    ```bash
    source venv/bin/activate
    export CENTER_URL="http://localhost:8000"
    python3 edge-agent/agent.py
    ```

4.  **Start Edge Agent** (Option B: Docker - Recommended):
    ```bash
    # Build and start using Docker Compose
    docker-compose -f docker-compose.agent.yml up --build -d
    ```
    *Note: The Docker deployment uses the DooD (Docker-out-of-Docker) pattern, requiring the host's `/var/run/docker.sock` to be mounted.*

5.  **Deploy a Game Server**:
    ```bash
    curl -X POST http://localhost:8000/games/deploy \
         -H "Content-Type: application/json" \
         -d '{"game_type": "minecraft", "owner_id": "player1"}'
    ```

## Features Implemented

*   **Node Registration**: Agents automatically register and report resource stats.
*   **Heartbeat System**: Agents report load average; Center tracks online status.
*   **Task Queue**: Center pushes tasks (e.g., DEPLOY) via heartbeat response.
*   **Deployment**: Agent pulls Docker image and runs container (Note: Requires Docker daemon).
*   **Save Sync**: Mock implementation supporting `local://` protocol to simulate S3 bucket for save data migration.

## Future Plans

*   Real S3/MinIO integration.
*   Frontend (React) Dashboard.
*   Automatic failover logic (Center detects offline -> Re-schedules on new node).
