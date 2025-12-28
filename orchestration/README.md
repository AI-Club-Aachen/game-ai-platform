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

### Base Image

The base image uses **Docker Hardened Images (DHI)** for Python 3.12. It runs as a non-root user and is "shell-free" in the final stage to prevent command injection attacks. 

It includes basic packages for ML and scientific computing (numpy, scipy, scikit-learn, networkx, numba). A GitHub Action rebuilds and pushes this to GHCR on changes. The workflow includes a Trivy security scan.

For local development (run from project root):

```bash
docker build -f orchestration/Dockerfile.base -t ghcr.io/aiclub-aachen/game-ai-platform/agent-base:latest orchestration/
```
