# AI SAV Platform

The project is split into two independently runnable applications:

- `frontend/`: React + Vite client application
- `backend/`: FastAPI API, database models, migrations, and tests

## Frontend

```bash
cd frontend
npm install
npm run dev
```

## Backend

Run the backend commands from `backend/` so the `app` package is on the Python path:

```bash
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run backend tests with `pytest` from the `backend/` directory. Database migrations are managed with the `alembic.ini` configuration in that directory.

## Docker

The root `docker-compose.yml` starts PostgreSQL and builds the backend from `backend/Dockerfile`.
