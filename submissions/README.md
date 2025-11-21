## Submissions

User submissions must be a `.zip` containing:

* **agent.py** or a file ending with `_agent.py` — this becomes the entrypoint

This directory includes:

* **agent_builder.py** — turns a submission ZIP into an Agent Docker image using `Dockerfile.agent`
* **agent_runner.py** — runs Agent containers with restricted settings
* **agent_manager.py** — lists, stops, deletes and inspects built images and containers
* **Dockerfile.base** — base image for all Agents (contains global Python environment)
* **Dockerfile.agent** — lightweight Agent image using the base image
* **base_requirements.txt** — global Python packages installed into the base image
* **secure_default_settings.yaml** — runtime and sandbox restrictions
* **default_dockerignore** — applied when the submission ZIP has no `.dockerignore`
* **tests/** — pytest tests (currently only very basic). Have to be run from the project root with:

    ```
    python -m pytest submissions/tests -v
    ```

### Base Image

If `Dockerfile.base` or `base_requirements.txt` changes, rebuild the base image manually:

```
docker build -f submissions/Dockerfile.base -t gameai-agent-base:latest submissions/
```
