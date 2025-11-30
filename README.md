# Game AI Platform

[![PyPI](https://img.shields.io/pypi/v/aica-gamelib)](https://pypi.org/project/aica-gamelib/)
[![Downloads](https://static.pepy.tech/badge/aica-gamelib)](https://pepy.tech/project/aica-gamelib)  
[![Tests-Backend](https://github.com/AI-Club-Aachen/game-ai-platform/actions/workflows/backend-pull-request-checks.yml/badge.svg)](https://github.com/AI-Club-Aachen/game-ai-platform/actions/workflows/backend-pull-request-checks.yml)
[![Tests-Gamelib](https://github.com/AI-Club-Aachen/game-ai-platform/actions/workflows/gamelib-pull-request-checks.yml/badge.svg)](https://github.com/AI-Club-Aachen/game-ai-platform/actions/workflows/gamelib-pull-request-checks.yml)
[![Tests-BaseImage](https://github.com/AI-Club-Aachen/game-ai-platform/actions/workflows/build-base-image.yml/badge.svg)](https://github.com/AI-Club-Aachen/game-ai-platform/actions/workflows/build-base-image.yml)

A comprehensive platform for hosting AI game competitions. Build your AI agent, compete against others, and climb the leaderboard.

## Quick Start

**Run the Platform Locally:**

1. **Backend:**
   ```bash
   cd backend
   docker-compose up --build
   # API at http://localhost:8000
   ```

2. **Frontend:**
   ```bash
   cd frontend
   pnpm install && pnpm run dev
   # UI at http://localhost:3000
   ```

3. **Install Gamelib (for agent development):**
   ```bash
   pip install aica-gamelib
   ```

## Project Structure

| Directory | Description | Documentation |
|-----------|-------------|---------------|
| **[backend/](backend/)** | FastAPI backend with PostgreSQL, JWT auth, and email verification | [Backend README](backend/README.md) |
| **[frontend/](frontend/)** | Next.js web UI for user registration, match viewing, and leaderboards | [Frontend README](frontend/README.md) |
| **[gamelib/](gamelib/)** | Core game logic and interfaces published to PyPI as `aica-gamelib` | [Gamelib README](gamelib/README.md) |
| **[submissions/](submissions/)** | Agent builder and runner for submissions | [Submissions README](submissions/README.md) |
| **[orchestrator/](orchestrator/)** | Match orchestrator handling containerized execution and networking | [Orchestrator README](orchestrator/README.md) |
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

**Technology Stack:**
- Backend: FastAPI, PostgreSQL, SQLModel, Redis, Alembic
- Frontend: Next.js, React, TypeScript
- Gamelib: Python 3.12+, pytest
- Orchestrator: Docker, Python
- Build Tool: uv (for Python dependencies)

## Contributing

1. Check out the component-specific READMEs for setup instructions
2. Run tests before submitting PRs
3. Follow the existing code style (ruff for Python, prettier for TypeScript)

## License

See individual component directories for license information.