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

### Running Locally
Start the development server:
```bash
bun run dev
```
The application will be available at `http://localhost:3000`.

### Building for Production
```bash
bun run build
```

## Testing
To run the detailed end-to-end tests using Playwright:
```bash
bunx playwright install
bun run test:e2e
bun run test:e2e:ui
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

## Tech Stack

- **Framework**: React + Vite
- **Language**: TypeScript
- **UI Library**: Material UI (MUI)
- **Routing**: React Router DOM
- **Styling**: Emotion (via MUI)
