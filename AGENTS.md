# Hidani project layout

This repository keeps the React/Vite frontend and Python backend in separate top-level folders: `frontend/` and `backend/`. Keep one root `.gitignore` for global ignores.

## Frontend

- `frontend/src/main.tsx` mounts the React application.
- `frontend/src/App.tsx` coordinates screens and API state.
- `frontend/src/components/` contains layout, jobs, profile, applications, and shared UI.
- `frontend/src/lib/api.ts` contains the API client.
- `frontend/package.json` defines npm scripts and dependencies.
- `frontend/vite.config.ts` configures React, Tailwind CSS v4, Figma Make, and proxies `/api` to `127.0.0.1:8001`.

Run the UI from `frontend/` with `npm install` and `npm run dev -- --port 8444`.

## Backend

- `backend/app/main.py` is the FastAPI entry point.
- `backend/app/api/` defines REST endpoints.
- `backend/app/agents/` implements job matching, chat orchestration, and application tracking.
- `backend/app/services/` parses uploaded resumes.
- `backend/data/` stores the public job catalogue and local user data.
- `backend/scripts/scrape_jobs.py` fetches public listings from configured ATS boards.
- `backend/.env` stores local secrets and must not be committed.

Install `backend/requirements.txt`, then run `uvicorn app.main:app --reload --host 127.0.0.1 --port 8001` from `backend/`.
