## Submissions

User submissions must be a `.zip` containing:

* **agent.py** or a file ending with `_agent.py` (must be in the root directory of the zip) — this becomes the entrypoint

This directory includes:

* **agent_builder.py** — turns a submission ZIP into an Agent Docker image using `Dockerfile.agent`
* **agent_runner.py** — runs Agent containers with restricted settings
* **agent_manager.py** — lists, stops, deletes and inspects built images and containers
* **Dockerfile.base** — base image for all Agents (contains global Python environment)
* **Dockerfile.agent** — lightweight Agent image using the base image
* **base_requirements.txt** — global Python packages installed into the base image
* **secure_default_settings.yaml** — runtime and sandbox restrictions
* **default_dockerignore** — applied when the submission ZIP has no `.dockerignore`
* **tests/** — pytest tests that have to be run from the project root with:

    ```
    python -m pytest submissions/tests -v
    ```

### Base Image

The base image is a slim Python 3.11 image that runs as a non-root user. It includes basic packages for ML and scientific computing (numpy, scipy, scikit-learn, networkx, numba). A GitHub Action rebuilds and pushes this to GHCR when you change `Dockerfile.base` or `base_requirements.txt` on main. The workflow builds for both amd64 and arm64, and runs a Trivy security scan.

For local development or if you need to rebuild manually:

```
docker build -f submissions/Dockerfile.base -t gameai-agent-base:latest submissions/
```
