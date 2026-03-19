# Spreadsheet Intelligence

Upload an Excel workbook and query it in plain English. Get exact answers backed by SQL — no guesswork, no hallucinated numbers.

---

## How it works

```
Upload .xlsx
     │
     ▼
gpt-4o-mini analyzes raw sheet layout
(header row, data start, rows to skip)
     │
     ▼
Schema profiled → column types, hints, sample values
     │
     ▼
gpt-4o detects cross-sheet relationships
(foreign keys, lookups, semantic joins)
     │
     ▼
text-embedding-3-small embeds each sheet → pgvector
     │
     ▼  (at query time)
     │
User question
     │
     ▼
pgvector retrieves relevant sheets
     │
     ▼
gpt-4o generates SQL (schema + relationships + question)
     │
     ▼
DuckDB executes SQL → exact answer
```

### Why SQL instead of asking the LLM to compute the answer

The LLM translates intent into SQL. DuckDB executes it. This means:
- Numbers are **always exact** — DuckDB does the arithmetic, not the LLM
- Answers are **verifiable** — the generated SQL is shown alongside every result
- Large datasets are handled without stuffing rows into the context window

---

## Key design decisions

### AI-assisted sheet structure detection
Excel files are presentation documents, not databases. They contain title rows, merged cell headers, embedded subtotals, footer annotations, and units sub-rows. Rather than hardcoding heuristics for each pattern, the app sends a raw sample of each sheet to `gpt-4o-mini` at upload time. The model identifies the true header row, data start row, and any rows to skip (subtotals, grand totals, metadata). A heuristic fallback handles the rare case where the LLM call fails — upload never breaks.

### Cross-sheet relationship graph
After profiling the schema, `gpt-4o` analyzes all sheets together to detect join-able relationships (e.g. `sales.Product ID → products.Product ID`, `sales.Sales Rep ID → employees.Rep ID`). These are stored on the workbook record and injected into the query planner's context. The query planner can then write JOIN queries automatically when a question spans multiple sheets — without the user needing to know the table structure.

### RAG for schema retrieval
Each sheet's schema is embedded with `text-embedding-3-small` and stored in pgvector. At query time, the question is embedded and the most semantically relevant sheets are retrieved. This keeps the prompt focused on relevant context rather than dumping the full workbook schema, which matters for workbooks with many sheets.

### Dirty data handling
Real-world Excel files have currency symbols (`$1,234`), percentage strings (`75%`), all-caps labels (`ENGINEERING`), and mixed numeric formats. The loader normalizes these at parse time so DuckDB sees clean typed columns. Column-level hints (e.g. `currency_strings`, `date_strings`, `numeric_as_text`) are passed to the query planner for any remaining edge cases.

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
| Structure detection | OpenAI `gpt-4o-mini` (once per sheet at upload) |
| Query planning | OpenAI `gpt-4o` |
| Relationship detection | OpenAI `gpt-4o` (once per workbook at upload) |
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
DATABASE_URL=postgresql://localhost/spreadsheet_intelligence
OPENAI_API_KEY=sk-...
CHAT_MODEL=gpt-4o
STRUCTURE_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
SECRET_KEY=change-me-in-production
UPLOAD_DIR=uploads
MAX_UPLOAD_SIZE_MB=50
```

### 4. Set up Postgres with pgvector

```bash
createdb spreadsheet_intelligence
psql spreadsheet_intelligence -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 5. Run database migrations

```bash
alembic upgrade head
```

### 6. Start the API

```bash
uvicorn app.main:app --reload
```

API available at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

### 7. Start the frontend

```bash
cd frontend
nvm use 20
npm install
npm run dev
```

Frontend available at `http://localhost:5173`.

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

### Query request

```json
POST /queries/
{
  "workbook_id": 1,
  "question": "What are total sales by product?"
}
```

### Query response

```json
{
  "question": "What are total sales by product?",
  "answer": [{"Product Name": "Enterprise Server Pro", "total_sales": 58498.05}, ...],
  "sql": "SELECT p.\"Product Name\", SUM(s.\"Quantity\" * s.\"Unit Price\") ...",
  "explanation": "Joins sales and products on Product ID, sums revenue per product.",
  "attribution": {"sheets": ["Sales", "Products"], "rows_matched": 5}
}
```

---

## Known limitations

**Multi-table sheets**: Excel sheets that contain two separate tables side-by-side or stacked are parsed as a single wide table. This affects lookup/reference sheets that combine multiple datasets in one tab.

**Unnamed formula columns**: Columns whose header cell is empty (typically formula-derived totals) get assigned a generic name like `col_7`. The query planner handles this correctly in most cases by inferring the column's purpose from context and adjacent columns, but the column name won't appear meaningfully in the schema panel.

**Formula recalculation**: Excel formulas are read as their last cached value (`data_only=True`). Formulas that reference external workbooks or volatile functions (`NOW()`, `TODAY()`) will show stale values.

**Mixed-currency aggregation**: Workbooks where the same column contains values in multiple currencies (USD and EUR in the same column) cannot be aggregated correctly without FX conversion. The query planner is instructed to flag this rather than return a misleading total.

**DuckDB is in-memory**: Workbook data is re-loaded from disk on server restart. There is no persistent DuckDB state between restarts (the data reloads automatically on first query after restart).

**Single-server only**: The DuckDB registry is an in-process dict. Horizontal scaling requires a shared cache layer (e.g. Redis + DuckDB file per workbook).

**File formats**: `.xlsx` only. `.xls`, `.csv`, and `.ods` are not supported.

---

## Project structure

```
├── app/
│   ├── main.py                      # FastAPI app, lifespan, CORS
│   ├── config.py                    # Environment config (pydantic-settings)
│   ├── database.py                  # SQLAlchemy engine + session
│   ├── models/                      # SQLAlchemy ORM models
│   ├── schemas/                     # Pydantic schemas (workbook, query, relationships)
│   ├── routes/
│   │   ├── workbooks.py             # Upload, list, get
│   │   └── queries.py               # Natural language query endpoint
│   ├── services/
│   │   ├── workbook_loader.py       # Excel → DataFrames (AI-assisted parsing)
│   │   ├── sheet_structure_analyzer.py  # gpt-4o-mini sheet layout detection
│   │   ├── schema_profiler.py       # Column type inference + hints
│   │   ├── relationship_detector.py # gpt-4o cross-sheet relationship detection
│   │   ├── embedding_service.py     # pgvector schema embeddings
│   │   ├── duckdb_registry.py       # In-memory DuckDB connections
│   │   ├── query_planner.py         # LLM → SQL with schema + relationship context
│   │   └── query_executor.py        # DuckDB execution + result formatting
│   └── prompts/
│       ├── query_planner.txt        # SQL generation prompt
│       ├── sheet_structure.txt      # Sheet layout detection prompt
│       └── relationship_detector.txt # Cross-sheet relationship prompt
├── alembic/                         # Database migrations
├── db/
│   └── schema.sql                   # Current database schema (like db/schema.rb)
├── frontend/                        # React + Vite
│   └── src/
│       ├── pages/                   # Home, WorkbookDetail
│       └── components/              # UploadZone, QueryChat, AnswerCard, SchemaPanel
├── tests/
│   └── test_documents/              # Sample workbooks for testing
├── uploads/                         # Uploaded files (gitignored)
├── requirements.txt
└── .env.example
```
