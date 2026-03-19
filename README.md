# Spreadsheet Intelligence

Upload an Excel workbook and query it in plain English. Get exact answers backed by SQL — no guesswork, no hallucinated numbers.

---

## Local development

### Prerequisites

- Python 3.10+
- Node 20+ (use [nvm](https://github.com/nvm-sh/nvm))
- PostgreSQL 15+
- pgvector extension (`brew install pgvector` on macOS)
- An OpenAI API key — estimated cost per workbook upload: ~$0.01–0.03 (structure analysis + relationship detection + embeddings). Query cost: ~$0.01–0.02 per question (gpt-4o). Typical full session under $0.10.

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
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=50
```

### 4. Set up Postgres with pgvector

```bash
# macOS
brew install pgvector

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
nvm install 20 && nvm use 20
npm install
npm run dev
```

Frontend available at `http://localhost:5173`.

---

## How it works

```
Upload .xlsx
     │
     ▼
openpyxl single-pass scan
(bold rows, merged regions, named ranges, print areas)
     │
     ▼
gpt-4o-mini analyzes raw sheet layout (parallel, one call per sheet)
(header row, data start, rows to skip, blank column renames)
     │
     ▼
Schema profiled → column types, hints, sample values
     │
     ▼
gpt-4o detects cross-sheet relationships
(foreign keys, lookups, semantic joins)
     │
     ▼
text-embedding-3-small embeds each sheet schema → pgvector
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
DuckDB executes SQL → exact answer + attribution
```

### Why SQL instead of asking the LLM to compute the answer

The LLM translates intent into SQL. DuckDB executes it. This means:
- Numbers are **always exact** — DuckDB does the arithmetic, not the LLM
- Answers are **verifiable** — the generated SQL is shown alongside every result
- Large datasets are handled without stuffing rows into the context window

---

## Key design decisions

### Single-pass openpyxl scan
The workbook is opened once with openpyxl. A pre-scan extracts rich formatting metadata — bold rows, merged cell regions, named ranges, print areas — into structured `SheetScan` models before any LLM call. This metadata is injected into the structure analysis prompt as explicit signals, so the LLM has concrete layout evidence rather than guessing from cell values alone. DataFrames are also built from this same open workbook, eliminating a second file read.

### AI-assisted sheet structure detection
Excel files are presentation documents, not databases. They contain title rows, merged cell headers, embedded subtotals, footer annotations, and units sub-rows. Rather than hardcoding heuristics for each pattern, the app sends a raw sample of each sheet to `gpt-4o-mini` at upload time, enriched with the openpyxl formatting metadata. The model identifies the true header row, data start row, any rows to skip (subtotals, grand totals, metadata), and infers names for blank header columns. Structure analysis runs in parallel across all sheets. A heuristic fallback handles the rare case where the LLM call fails — upload never breaks.

### Blank header column reliability
If the first LLM call returns an incomplete rename for blank header positions, a second targeted call fires automatically with an explicit annotation listing the missed positions. This makes blank column name inference reliable across repeated uploads rather than flaky.

### Cross-sheet relationship detection
After profiling the schema, `gpt-4o` analyzes all sheets together to detect join-able relationships (e.g. `sales.Product ID → products.Product ID`, `sales.Sales Rep ID → employees.Rep ID`). These are stored on the workbook record and injected into the query planner's context so JOIN queries are written automatically when a question spans multiple sheets.

### Schema embeddings for retrieval
Each sheet's schema is embedded with `text-embedding-3-small` and stored in pgvector. At query time, the question is embedded and the most semantically relevant sheets are retrieved. This keeps the query planner prompt focused on relevant context rather than dumping the full workbook schema.

### Self-correcting query execution
If the generated SQL fails, the error is sent back to the LLM for one self-correction attempt before surfacing to the user. This handles type mismatches, unexpected column values, and DuckDB dialect edge cases without requiring manual intervention.

### Dirty data handling
Real-world Excel files have currency symbols (`$1,234`), percentage strings (`75%`), all-caps labels (`ENGINEERING`), comma-formatted numbers, and empty-string cells from merged regions. The loader normalizes these at parse time. Column-level hints (`currency_strings`, `percent_strings`, `date_strings`, `numeric_as_text`) are passed to the query planner for any remaining edge cases at query time.

---

## Tech stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Frontend | React + Vite |
| App database | PostgreSQL + pgvector |
| Query engine | DuckDB (in-memory) |
| Excel parsing | openpyxl + pandas |
| Embeddings | OpenAI `text-embedding-3-small` |
| Structure detection | OpenAI `gpt-4o-mini` (parallel, once per sheet at upload) |
| Query planning | OpenAI `gpt-4o` |
| Relationship detection | OpenAI `gpt-4o` (once per workbook at upload) |
| Migrations | Alembic |

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
  "sql": "SELECT p.\"Product Name\", SUM(s.\"Total Sales\") ...",
  "explanation": "Joins sales and products on Product ID, sums revenue per product.",
  "attribution": {"sheets": ["Sales", "Products"], "rows_matched": 5}
}
```

---

## Known limitations

**Formula recalculation**: Excel formulas are read as their last cached value (`data_only=True`). Formulas that reference external workbooks or volatile functions (`NOW()`, `TODAY()`) will show stale values. Files with uncached formulas display a warning on upload.

**Mixed-currency aggregation**: Workbooks where the same column contains values in multiple currencies (USD and EUR in the same column) cannot be aggregated correctly without FX conversion. The query planner is instructed to flag this rather than return a misleading total.

**Transposed/pivot-style sheets**: Sheets where rows are metrics and columns are time periods (KPI dashboards, pivot exports) are parsed as-is. Queries against these sheets need to reference the metric name by row value rather than column name, which natural language questions don't always make explicit.

**DuckDB is in-memory**: Workbook data is re-loaded from disk on server restart. Re-registration happens automatically on the first query after restart — no data is lost, but the first query after a cold start is slower.

**Single-server only**: The DuckDB registry is an in-process dict. Horizontal scaling requires a shared cache layer (e.g. Redis + DuckDB file per workbook).

**File formats**: `.xlsx` only. `.xls`, `.csv`, and `.ods` are not supported.

---

## Project structure

```
├── app/
│   ├── main.py                          # FastAPI app, lifespan, CORS
│   ├── config.py                        # Environment config (pydantic-settings)
│   ├── database.py                      # SQLAlchemy engine + session
│   ├── models/                          # SQLAlchemy ORM models
│   ├── schemas/                         # Pydantic schemas (workbook, query, relationships)
│   ├── routes/
│   │   ├── workbooks.py                 # Upload, list, get
│   │   └── queries.py                   # Natural language query + self-correction loop
│   ├── services/
│   │   ├── workbook_scanner.py          # Single openpyxl pass — formatting metadata extraction
│   │   ├── workbook_loader.py           # Excel → DataFrames (AI-assisted parsing pipeline)
│   │   ├── sheet_structure_analyzer.py  # gpt-4o-mini sheet layout detection + retry logic
│   │   ├── schema_profiler.py           # Column type inference + dirty data hints
│   │   ├── relationship_detector.py     # gpt-4o cross-sheet relationship detection
│   │   ├── embedding_service.py         # pgvector schema embeddings + retrieval
│   │   ├── duckdb_registry.py           # In-memory DuckDB connections per workbook
│   │   ├── query_planner.py             # LLM → SQL with schema + relationship context
│   │   └── query_executor.py            # DuckDB execution + result formatting
│   └── prompts/
│       ├── query_planner.txt            # SQL generation prompt
│       ├── sheet_structure.txt          # Sheet layout detection prompt
│       └── relationship_detector.txt    # Cross-sheet relationship prompt
├── alembic/                             # Database migrations
├── scripts/
│   └── generate_test_files.py           # Generates stress-test xlsx files for edge case testing
├── frontend/                            # React + Vite
│   └── src/
│       ├── pages/                       # Home, WorkbookDetail
│       └── components/                  # UploadZone, QueryChat, AnswerCard, SchemaPanel
├── uploads/                             # Uploaded files (gitignored)
├── requirements.txt
└── .env.example
```
