# AI Game Competition Platform - Frontend

The frontend for the AI Game Competition Platform, built with React, Vite, and Material UI.

## Getting Started

### Prerequisites
- [Bun](https://bun.sh) (v1.0+)

#### Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

### Installation
Install dependencies:
   ```bash
   bun install
   ```

### Building for Production
```bash
bun run build
```

## Testing
Install Playwright browsers once:
```bash
bunx playwright install
```

Start the backend test stack from the repo root:
```bash
docker compose --env-file .env -f backend/docker-compose.ci.yml up -d --build redis db backend agent-builder
```

Then run the full Playwright suite from `frontend/`:
```bash
bun run test:e2e
bun run test:e2e:ui
```

To dry-run the GitHub Actions pipelines locally with `act` from the repo root:
```bash
act pull_request -W .github/workflows/playwright.yml -j ui-test
act push -W .github/workflows/playwright.yml -j build-e2e
```


## Project Structure

```
frontend/
├── src/
│   ├── components/     # Reusable UI components
│   ├── context/        # Global state (AuthContext)
│   ├── pages/          # Page components (Routing targets)
│   ├── services/       # API communication layer
│   ├── config/         # Configuration files
│   ├── App.tsx         # Main application component & Routing
│   ├── main.tsx        # Entry point
│   └── theme.ts        # Material UI theme configuration
```

## Key Features

- **Authentication**: Login, Register, Email Verification using JWT.
- **Dashboard**: User overview of games and stats.
- **Game Management**: Browse games, view rules, and leaderboards.
- **Live & Past Games**: Watch live matches or review history.
- **Tournament System**: Participate in organized tournaments.
- **Container Management**: Manage AI containers.

## Configuration

The application uses environment variables for configuration.
- `VITE_API_URL`: Backend API URL (default: `http://localhost:8000`)
- `MAX_TURN_TIME_LIMIT_SECONDS`: UI cap for per-turn time limit (default: `120`)

## Tech Stack

- **Framework**: React + Vite
- **Language**: TypeScript
- **UI Library**: Material UI (MUI)
- **Routing**: React Router DOM
- **Styling**: Emotion (via MUI)
