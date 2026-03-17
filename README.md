# Spreadsheet Intelligence

Upload an Excel workbook and query it in plain English. Get exact answers backed by SQL — no guesswork, no hallucinated numbers.

---

## How it works

1. **Upload** an `.xlsx` file — the app parses every sheet, profiles the schema, and stores embeddings of each sheet's structure in Postgres.
2. **Ask a question** in natural language — GPT-4o translates your intent into SQL using only the relevant sheets (found via vector similarity search).
3. **DuckDB executes the SQL** against the actual data and returns an exact answer. The LLM never does arithmetic.

```
User question
     │
     ▼
pgvector similarity search  →  relevant sheets
     │
     ▼
GPT-4o (schema + question)  →  SQL
     │
     ▼
DuckDB executes SQL          →  exact answer
```

---

## Tech stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Frontend | React + Vite |
| App database | PostgreSQL + pgvector |
| Query engine | DuckDB (in-memory) |
| Excel parsing | pandas + openpyxl |
| Embeddings | OpenAI `text-embedding-3-small` |
| Query planning | OpenAI `gpt-4o` |
| Migrations | Alembic |

---

## Local development

### Prerequisites

- Python 3.13+
- Node 20+ (use [nvm](https://github.com/nvm-sh/nvm))
- PostgreSQL 15+ with the `pgvector` extension
- An OpenAI API key

### 1. Clone the repo

```bash
git clone git@github.com:Brandongoodman615/spreadsheet-intelligence.git
cd spreadsheet-intelligence
```

### 2. Set up Python environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/spreadsheet_intelligence
OPENAI_API_KEY=sk-...
CHAT_MODEL=gpt-4o
EMBEDDING_MODEL=text-embedding-3-small
SECRET_KEY=change-me-in-production
UPLOAD_DIR=uploads
MAX_UPLOAD_SIZE_MB=50
```

### 4. Set up Postgres with pgvector

```bash
# Create the database
psql -U postgres -c "CREATE DATABASE spreadsheet_intelligence;"

# Enable pgvector extension
psql -U postgres -d spreadsheet_intelligence -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 5. Run database migrations

```bash
alembic upgrade head
```

### 6. Start the API

```bash
uvicorn app.main:app --reload
```

API is available at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

### 7. Start the frontend

```bash
cd frontend
nvm use 20
npm install
npm run dev
```

Frontend is available at `http://localhost:5173`.

---

## API reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/workbooks/` | Upload an `.xlsx` file |
| `GET` | `/workbooks/` | List all uploaded workbooks |
| `GET` | `/workbooks/{id}` | Get workbook schema |
| `POST` | `/queries/` | Run a natural language query |
| `GET` | `/queries/{workbook_id}/history` | Get query history for a workbook |
| `GET` | `/health` | Health check |

---

## Production deployment

### Environment

Set these in addition to the local env vars:

```env
APP_ENV=production
SECRET_KEY=<strong-random-secret>
DATABASE_URL=postgresql://user:password@your-db-host:5432/spreadsheet_intelligence
```

### Database

Run migrations against your production database before deploying:

```bash
DATABASE_URL=postgresql://... alembic upgrade head
```

Ensure the `pgvector` extension is enabled on your Postgres instance. Most managed providers (Supabase, Neon, Railway) support it natively.

### API

```bash
# Install production dependencies
pip install -r requirements.txt

# Run with multiple workers
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Or use gunicorn with the uvicorn worker class:

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Frontend

```bash
cd frontend
npm install
npm run build
# Serve the dist/ directory with nginx, Caddy, or any static host
```

Point your reverse proxy (nginx, Caddy) at:
- `/` → frontend `dist/` directory
- `/workbooks`, `/queries`, `/health` → API on port 8000

### Uploads

The `uploads/` directory stores the original `.xlsx` files on disk. In production, replace local storage with S3 or another object store and update `settings.upload_path` accordingly.

---

## Known limitations

- **Formula support**: Excel formulas are detected but executed values are used (not recalculated). Formulas that depend on external data sources will not work.
- **File size**: Default limit is 50MB. Adjust `MAX_UPLOAD_SIZE_MB` in `.env`.
- **Supported formats**: `.xlsx` only. `.xls` and `.csv` are not supported.
- **DuckDB is in-memory**: Workbook data is re-loaded from disk on server restart. There is no persistent DuckDB state.
- **Single-server only**: The DuckDB registry is an in-process dict. Horizontal scaling requires a shared cache layer (e.g. Redis + DuckDB file per workbook).

---

## Project structure

```
├── app/
│   ├── main.py               # FastAPI app entry point
│   ├── config.py             # Environment config (pydantic-settings)
│   ├── database.py           # SQLAlchemy engine + session
│   ├── models/               # SQLAlchemy models
│   ├── schemas/              # Pydantic schemas
│   ├── routes/               # API route handlers
│   ├── services/             # Business logic
│   │   ├── workbook_loader.py    # Excel parsing
│   │   ├── schema_profiler.py    # Schema extraction
│   │   ├── duckdb_registry.py    # In-memory DuckDB connections
│   │   ├── embedding_service.py  # pgvector embeddings
│   │   ├── query_planner.py      # LLM → SQL
│   │   └── query_executor.py     # DuckDB execution
│   └── prompts/              # LLM prompt templates
├── alembic/                  # Database migrations
├── frontend/                 # React + Vite app
│   └── src/
│       ├── pages/            # Home, WorkbookDetail
│       └── components/       # UploadZone, QueryChat, AnswerCard, SchemaPanel
├── uploads/                  # Uploaded workbooks (gitignored)
├── requirements.txt
└── .env.example
```
