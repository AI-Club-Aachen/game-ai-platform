# Game AI Platform

[![PyPI](https://img.shields.io/pypi/v/aica-gamelib)](https://pypi.org/project/aica-gamelib/)
[![Downloads](https://static.pepy.tech/badge/aica-gamelib)](https://pepy.tech/project/aica-gamelib)  
[![Tests-Backend](https://github.com/AI-Club-Aachen/game-ai-platform/actions/workflows/backend-pull-request-checks.yml/badge.svg)](https://github.com/AI-Club-Aachen/game-ai-platform/actions/workflows/backend-pull-request-checks.yml)
[![Tests-Gamelib](https://github.com/AI-Club-Aachen/game-ai-platform/actions/workflows/gamelib-pull-request-checks.yml/badge.svg)](https://github.com/AI-Club-Aachen/game-ai-platform/actions/workflows/gamelib-pull-request-checks.yml)
[![Tests-BaseImage](https://github.com/AI-Club-Aachen/game-ai-platform/actions/workflows/build-base-image.yml/badge.svg)](https://github.com/AI-Club-Aachen/game-ai-platform/actions/workflows/build-base-image.yml)

A comprehensive platform for hosting AI game competitions. Build your AI agent, compete against others, and climb the leaderboard.

## Quick Start

**Run the Whole Platform for Local Development:**
1. Start all services with the explicit development override (Backend, Vite frontend, Database, Redis):
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
   ```
2. Access the platform:
   - **Frontend:** http://localhost:3000
   - **Backend API:** http://localhost:8000
   - **API Docs:** http://localhost:8000/docs

**Production / Dokploy Compose:**

The root `docker-compose.yml` is production-oriented by default. It builds the frontend's `production` Docker target, where nginx serves the compiled React/Vite assets behind the external reverse proxy (for example Traefik in Dokploy):

```bash
docker compose -f docker-compose.yml up -d --build
```

Local development settings live in `docker-compose.dev.yml` and must be opted into explicitly. `docker-compose.override.yml` is intentionally empty so that development-only frontend settings are not accidentally applied in production deployments.

After a production deploy, the frontend container should run nginx, not Vite. A quick sanity check is:

```bash
docker inspect <compose-project>-frontend-1 --format 'Cmd={{json .Config.Cmd}}'
```

Expected output includes `nginx`; output such as `bun run dev --host` means a development compose override was applied.

**Install Gamelib (for agent development):**
```bash
pip install aica-gamelib
```

## Project Structure

| Directory | Description | Documentation |
|-----------|-------------|---------------|
| **[backend/](backend/)** | FastAPI backend with PostgreSQL, JWT auth, and email verification | [Backend README](backend/README.md) |
| **[frontend/](frontend/)** | React + Vite web UI for user registration, match viewing, and leaderboards | [Frontend README](frontend/README.md) |
| **[gamelib/](gamelib/)** | Core game logic and interfaces published to PyPI as `aica-gamelib` | [Gamelib README](gamelib/README.md) |
| **[orchestration/](orchestration/)** | Agent building, containerized execution, and match orchestration | [Orchestration README](orchestration/README.md) |
| **[tests/](tests/)** | Cross-component integration tests | [Tests README](tests/README.md) |
| **[docs/](docs/)** | General documentation and specifications | [Docs README](docs/README.md) |

## Features

- **Modular Game System** - Easy to add new games via the gamelib interface
- **Secure Authentication** - JWT-based auth with role-based access control
- **Email Verification** - Automated email verification and password reset flows
- **Containerized Execution** - Isolated agent execution in Docker containers
- **Leaderboards & Matches** - Track performance and view match replays
- **Comprehensive Testing** - Unit tests for backend, gamelib, and integration tests
- **CI/CD Pipeline** - Automated testing and deployment workflows

## Documentation

- **Platform Specification**: [Docmost Pages](https://docs.ai-club-aachen.com/share/qrd5l63ot8/p/game-ai-platform-specification-jwpB7TeFmd)
- **API Documentation**: `http://localhost:8000/docs` (when running locally)
- **PyPI Package**: [aica-gamelib](https://pypi.org/project/aica-gamelib/)

## Development

Each component has its own README with detailed setup instructions. See the table above for direct links.

For full-stack local development with hot reload, use:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Avoid putting development-only settings in `docker-compose.override.yml`; Compose applies that file automatically for plain `docker compose up`, which can accidentally switch production from the nginx frontend image to the Vite dev server.

**Technology Stack:**
- Backend: FastAPI, PostgreSQL, SQLModel, Redis, Alembic
- Frontend: React, Vite, TypeScript
- Gamelib: Python 3.12+, pytest
- Orchestration: Docker, Python
- Build Tool: uv (for Python dependencies)

## Contributing

1. Check out the component-specific READMEs for setup instructions
2. Run tests before submitting PRs
3. Follow the existing code style (ruff for Python, prettier for TypeScript)

## License

See individual component directories for license information.