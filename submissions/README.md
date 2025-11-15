## Submissions

User submissions must be a `.zip` containing:

* **agent.py** — required entrypoint
* **requirements.txt** — optional

This directory includes:

* **agent_builder.py** — builds a Docker image from a submitted ZIP. Use `build_from_zip(data, owner_id)` to turn a ZIP's bytes into a tagged Docker image.
* **agent_runner.py** — provides two run modes:

  * `run_agent(image_ref)` for local or short test runs
  * `start_agent_container(image_ref, match_id=..., agent_id=..., owner_id=...)` for long-running match containers
* **Dockerfile** — base image used for all agents
* **secure_default_settings.yaml** — resource and sandbox settings used when running containers
* **default_dockerignore** — applied when the submission ZIP does not include a `.dockerignore`
* **tests/** — pytest tests (planned)