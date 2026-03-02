# QA Agent - Full System Documentation

This repository contains an AI-powered QA platform with:

- A Python/FastAPI backend that orchestrates LLM-guided QA runs and executes QA tools.
- A Next.js frontend that submits scans and renders detailed reports.
- A modular tool + provider architecture with mistral model as core engine.

For architecture details, see [architecure.md](./architecure.md).

## 1. What This System Does

Given a target URL, the system can run an autonomous QA mission that checks:

- Functional behavior (links, forms, button/action patterns, auth/session flows)
- UX and accessibility risk signals
- Performance metrics
- Security headers, SSL, and content risks
- Browser network/console evidence

It returns:

- Structured issues (severity, category, reproducible steps)
- Tool outputs and execution trace
- Screenshots (served by backend)
- Raw model output for auditability

## 2. Tech Stack

Backend:

- Python 3.11+
- FastAPI + Uvicorn
- Playwright
- Pydantic / pydantic-settings
- LLM providers: Mistral, Hugging Face

Frontend:

- Next.js 15 (App Router)
- React 18
- TypeScript
- Tailwind CSS
- TanStack Query

## 3. Repository Structure

```text
.
|-- engine/                  # Core orchestration, providers, tools, prompts
|   |-- core/                # Agent loop + parsing + typed results
|   |-- providers/           # LLM provider abstraction + implementations
|   |-- prompts/             # System/user prompt builders
|   |-- tools/               # QA tool implementations
|-- server/                  # FastAPI app, schemas, service wiring
|-- web/                     # Next.js frontend
|-- artifacts/screenshots/   # Runtime screenshot artifacts (served by backend)
|-- tests/                   # Backend and tool tests
|-- .env.example             # Environment template
|-- requirements.txt
|-- pyproject.toml
```

## 4. Prerequisites

- Python 3.11+
- Node.js 18+
- npm or yarn
- Playwright browser binaries

## 5. Environment Variables

Create `.env` from `.env.example`:

```env
APP_ENV=local
PROVIDER_NAME=mistral
PROVIDER_MODEL=mistral-large-latest
PROVIDER_API_KEY=your_provider_key
API_AUTH_SECRET=replace_with_long_random_secret
```

Backend reads these via `server/config.py`.

Frontend environment variables (`web/.env`):

```env
NEXT_PUBLIC_QA_API_URL=http://localhost:8000/api/qa
NEXT_PUBLIC_QA_API_KEY=replace_with_same_api_auth_secret
```

Important:

- `NEXT_PUBLIC_QA_API_KEY` must match backend `API_AUTH_SECRET`.
- If `PROVIDER_API_KEY` is missing, backend QA execution fails by design.

## 6. Local Development Setup

### 6.1 Backend

From repository root:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

Backend endpoints:

- Root health: `GET /`
- QA endpoint: `POST /api/qa`
- Screenshots static path: `/screenshots/*`
- OpenAPI docs (non-production): `/docs`

### 6.2 Frontend

From repository root:
```bash
cd web
npm install
npm run dev
```

Default frontend URL: `http://localhost:3000`

## 7. How a Scan Works (End-to-End)

1. User submits a scan from `/qa` page (target URL + device/network/tool selections).
2. Frontend calls backend `POST /api/qa` with API key header.
3. Backend normalizes URL and creates `QATask`.
4. `Engine` initializes provider + Playwright-backed/static tools.
5. `QAOrchestrator` runs model-tool loop:
   - model proposes tool calls
   - tools execute and return structured payloads
   - tool outputs feed back into model context
6. Model emits final JSON issues payload.
7. Backend serializes tool outputs and persists base64 screenshots to `artifacts/screenshots`.
8. Backend returns issues + trace + screenshot URLs.
9. Frontend adapts backend response into report model and renders `/qa/results`.

## 8. Development and Quality Commands

Backend checks:

```bash
ruff check .
mypy .
pytest -q
```

Frontend checks:

```bash
cd web
npm run typecheck
npm run lint
```

## 9. Extending the System

Add a new tool:

1. Implement class extending `BaseTool`.
2. Register it in `engine/tools/maps.py`.
3. Add request schema key in `server/schemas.py` (`ToolKey` literal).
4. Expose selection in frontend type `web/types/scan.ts`.
5. Add tests under `tests/`.

Add a new provider:

1. Implement `BaseLLMProvider`.
2. Register in `ProviderRegistry`.
3. Set `PROVIDER_NAME` and `PROVIDER_MODEL` in environment.

## 10. Docker (Run Web + Backend Together)

### 10.1 Prerequisites

- Docker Desktop running
- Docker Compose v2 (`docker compose`)

### 10.2 Prepare `.env` (root)

Create/update root `.env`:

```env
APP_ENV=local
PROVIDER_NAME=mistral
PROVIDER_MODEL=mistral-large-latest
PROVIDER_API_KEY=your_real_provider_key
API_AUTH_SECRET=local-dev-auth-secret-change-me
NEXT_PUBLIC_QA_API_URL=http://localhost:8000/api/qa
```

Notes:
- Frontend API key is auto-wired from `API_AUTH_SECRET` in `docker-compose.yml`.
- `NEXT_PUBLIC_*` variables are build-time values for Next.js.

### 10.3 Build and Start

From repository root:

```bash
docker compose up --build
```

Services:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs` (non-production)

### 10.4 Stop

```bash
docker compose down
```

### 10.5 Logs

```bash
docker compose logs -f
```

### 10.6 Rebuild When Frontend Env Changes

If you change any `NEXT_PUBLIC_*` values:

```bash
docker compose up --build
```

### 10.7 Troubleshooting Slow Build / "resolving provenance"

If build appears stuck for several minutes on provenance metadata:

```powershell
$env:BUILDX_NO_DEFAULT_ATTESTATIONS="1"
docker compose build --progress=plain
docker compose up
```

Also note:
- First backend image pull is large (Playwright base image), so first run can be slow.
- If needed, pre-pull once: `docker pull mcr.microsoft.com/playwright/python:v1.58.0-jammy`.
