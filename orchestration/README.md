## Orchestration

User submissions must be a `.zip` containing:

* **agent.py** or a file ending with `_agent.py` (must be in the root directory of the zip) — this becomes the entrypoint

This directory includes:

* **agent_builder_worker.py** — Redis worker for processing build jobs
* **match_runner_worker.py** — Redis worker for processing match jobs
* **lib/** — Core orchestration logic:
    * **agent_builder.py** — creates Agent images using `Dockerfile.agent`
    * **agent_runner.py** — runs Agent containers with restricted settings
    * **agent_manager.py** — utility for inspecting images/containers
* **Dockerfile.base** — base image using Docker Hardened Images (DHI)
* **Dockerfile.agent** — lightweight Agent image build template
* **base_requirements.txt** — global Python packages for the base image
* **secure_default_settings.yaml** — runtime and sandbox restrictions
* **default_dockerignore** — applied when the submission ZIP has no `.dockerignore`
* **tests/** — pytest tests run with:

    ```bash
    uv run python -m pytest
    ```

### Agent Image Construction

The base image uses **Docker Hardened Images (DHI)** for Python 3.12. It runs as a non-root user and is "shell-free" in the final stage to prevent command injection attacks. 

It includes basic packages for ML and scientific computing (numpy, scipy, scikit-learn, networkx, numba). A GitHub Action rebuilds and pushes this to GHCR on changes. The workflow includes a Trivy security scan.

To use Docker Hardened Images, first login before building:

```bash
docker login dhi.io
```

`Dockerfile.base` is built into an image and published as `ghcr.io/ai-club-aachen/game-ai-platform/agent-base:latest`.

For local development (run from project root):

```bash
docker build -f orchestration/Dockerfile.base -t ghcr.io/aiclub-aachen/game-ai-platform/agent-base:latest orchestration/
```

The base imaged is used as the foundation for building Agent images in `Dockerfile.agent`.

### Workers

Workers use `Dockerfile.worker` and run either `agent_builder_worker.py` or `match_runner_worker.py`.

Workers gather tasks from Redis queues and process them.

Run `uv sync` before building because workers use `uv.lock` for dependencies.

#### Connection to Backend

The workers connect to the backend API and redis. Set the `BACKEND_URL` and `REDIS_URL` environment variables in `.env` of the root project directory:

```
BACKEND_URL=http://localhost:8000/api/v1
REDIS_URL=redis://redis:6379/0
```