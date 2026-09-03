# KholleLab

KholleLab is a blackboard-first mathematics practice web app inspired by French oral *khôlles*: solve a problem on a board, ask for controlled hints, then compare the reasoning with a reference solution.

## PR1 scope

This foundation slice provides:

- React + TypeScript + Vite frontend
- tldraw blackboard surface
- KaTeX rendering for problem statements
- FastAPI backend with health and demo-problem endpoints
- PostgreSQL service reserved for persistence work starting in the next PRs
- Docker Compose topology compatible with a first Coolify deployment
- GitHub Actions for backend checks, frontend checks and a Compose smoke test

LLM grading, authentication and persistence are intentionally out of scope for PR1.

## Local run

```bash
cp .env.example .env
docker compose up --build
```

Then open `http://localhost:8080`.

Health check:

```bash
curl http://localhost:8080/api/v1/health
```

## Development

Backend:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e './backend[dev]'
uvicorn app.main:app --app-dir backend --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://localhost:8000`.

## CI contract

Every pull request must keep these commands green:

```bash
python -m compileall -q backend/app
ruff check backend
pytest -q backend/tests
cd frontend && npm run typecheck && npm run test -- --run && npm run build
docker compose config
docker compose up -d --build
./scripts/smoke.sh
docker compose down -v
```

## Coolify

Deploy the repository as a Docker Compose application. Route the public domain to the `web` service on port `80`; `api` and `db` remain internal. Set a strong `POSTGRES_PASSWORD` in Coolify rather than committing it.

The production web container proxies `/api/*` to the FastAPI service, so the browser only needs the public frontend origin.
