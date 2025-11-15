## Submissions

User submissions must be a `.zip` containing:

* **agent.py** — required entrypoint
* **requirements.txt** — optional

This directory includes:

* **agent_builder.py** — builds a Docker image from the submitted ZIP
* **agent_runner.py** — runs a built image with security and resource limits
* **Dockerfile** — fixed base image for all agents
* **secure_default_settings.yaml** — runtime and sandbox settings
* **default_dockerignore** — fallback ignore list when the ZIP has none
* **tests/** — pytest tests (planned)
