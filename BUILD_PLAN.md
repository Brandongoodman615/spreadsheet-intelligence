# Spreadsheet Intelligence — Build Plan

## Assignment Summary
Upload `.xlsx` files → ask natural language questions → get **exact** answers with generated SQL and source attribution.

**Key constraint:** Numerical answers must be exactly correct. AI plans the query. DuckDB executes it.

---

## Stack

| Layer | Tool | Rails Equivalent |
|-------|------|-----------------|
| Web framework | FastAPI | Rails |
| Templates | Jinja2 | ERB |
| Reactive UI | HTMX + Alpine.js | Hotwire / Turbo |
| App database | Postgres | Postgres |
| ORM | SQLAlchemy | ActiveRecord |
| Validation | Pydantic | Strong params + model validations |
| Excel parsing | pandas + openpyxl | — |
| Analytics engine | DuckDB | — |
| LLM | Anthropic Claude | — |
| Styles | Tailwind (CDN) | — |

---

## Folder Structure

```
spreadsheet-intelligence/
├── app/
│   ├── main.py                      # FastAPI app entry, route registration
│   ├── database.py                  # SQLAlchemy setup, session management
│   ├── config.py                    # Settings via env vars (pydantic-settings)
│   │
│   ├── routes/
│   │   ├── workbooks.py             # Upload, show, list
│   │   └── queries.py               # Natural language query endpoint
│   │
│   ├── services/
│   │   ├── workbook_loader.py       # Read .xlsx → dict of DataFrames
│   │   ├── schema_profiler.py       # Inspect sheets → WorkbookSchema summary
│   │   ├── query_planner.py         # LLM call → structured QueryPlan
│   │   ├── query_executor.py        # QueryPlan → SQL → DuckDB → result
│   │   ├── attribution_builder.py   # Build source attribution from plan + result
│   │   └── duckdb_registry.py       # Register DataFrames in DuckDB per session
│   │
│   ├── models/
│   │   ├── workbook.py              # Workbook DB record (SQLAlchemy)
│   │   └── query_log.py             # Query history per workbook (SQLAlchemy)
│   │
│   ├── schemas/
│   │   ├── workbook.py              # Pydantic: WorkbookSchema, SheetSchema
│   │   └── query.py                 # Pydantic: QueryPlan, QueryResult
│   │
│   ├── prompts/
│   │   └── query_planner.txt        # LLM system prompt for query planning
│   │
│   ├── templates/
│   │   ├── base.html
│   │   ├── workbooks/
│   │   │   ├── index.html           # Upload page
│   │   │   └── show.html            # Workbook detail + chat panel
│   │   └── partials/
│   │       ├── schema_sidebar.html  # Sheets + columns summary
│   │       ├── query_form.html      # Natural language input
│   │       ├── answer_card.html     # Answer + SQL + attribution
│   │       └── query_history.html   # Previous queries for this workbook
│   │
│   └── static/
│       ├── app.css
│       └── app.js                   # Minimal Alpine.js init if needed
│
├── uploads/                         # Stored .xlsx files (local for MVP)
├── tests/
│   └── test_documents/              # company_data.xlsx, testdata.xlsx
├── .env.example
├── requirements.txt
├── README.md
└── BUILD_PLAN.md
```

---

## Data Flow

```
User uploads .xlsx
        │
        ▼
workbook_loader.py
  → pandas.read_excel(sheet_name=None)
  → openpyxl for workbook-level metadata
  → returns: { sheet_name: DataFrame, ... }
        │
        ▼
schema_profiler.py
  → for each sheet: name, columns, dtypes, row count, sample rows
  → returns: WorkbookSchema (Pydantic)
        │
        ▼
Save WorkbookSchema to Postgres
Register DataFrames in DuckDB
Show workbook detail page
        │
User asks natural language question
        │
        ▼
query_planner.py  ← LLM (Claude)
  Input:  question + WorkbookSchema summary
  Output: QueryPlan (Pydantic)
    {
      "relevant_sheets": ["Sales"],
      "sql": "SELECT SUM(revenue) FROM sales WHERE region = 'West'",
      "explanation": "Sum revenue from Sales where region = West"
    }
        │
        ▼
query_executor.py
  → run SQL against DuckDB
  → return exact result + matched row count
        │
        ▼
attribution_builder.py
  → sheets used, columns used, rows matched
        │
        ▼
Render answer_card partial (HTMX swap)
  → Answer
  → Generated SQL
  → Source attribution
  → Optional: preview rows
Save to query_log
```

---

## LLM Role (narrow and intentional)

**LLM does:**
- Map user question → relevant sheets/columns
- Generate SQL for DuckDB execution
- Write a plain-English explanation of what was computed

**LLM does NOT:**
- Do arithmetic
- Answer directly from raw spreadsheet data
- Infer values without running a query

**Why:** Correctness. The LLM is a translator, not a calculator.

**If asked about RAG in review:**
> "I intentionally didn't use classic RAG because the source material is structured tabular data, not unstructured documents. I used the model for semantic schema mapping and SQL generation, then delegated all computation to a deterministic query engine."

---

## Workbook Loading — Key Detail

```python
# openpyxl: data_only=True returns cached formula values
# Does NOT recalculate formulas — explicitly disclaimed in README
wb = openpyxl.load_workbook(file, data_only=True)

# pandas: load all sheets at once
frames = pandas.read_excel(file, sheet_name=None, engine="openpyxl")
```

Formula cells: cached values are used when available. Full recalculation is not supported.
This is explicitly noted as a known limitation.

---

## DuckDB Setup

```python
import duckdb
import pandas as pd

# Per-workbook: register all sheets as DuckDB tables
conn = duckdb.connect()
for sheet_name, df in frames.items():
    table_name = normalize_table_name(sheet_name)  # "Sales Data" → "sales_data"
    conn.register(table_name, df)

# Now query with standard SQL
result = conn.execute("SELECT SUM(revenue) FROM sales_data WHERE region = 'West'").fetchdf()
```

DuckDB vs Postgres for this layer:
- No schema migration needed
- Queries DataFrames directly in memory
- SQL is standard — easy to inspect and show users
- Use Postgres only for app data (workbook records, query history)

---

## App DB Schema (SQLAlchemy / Postgres)

```
workbooks
  id, filename, original_name, upload_path,
  schema_json, sheet_count, created_at

query_logs
  id, workbook_id, question, generated_sql,
  answer_raw, attribution_json, created_at
```

---

## UI Layout

```
┌─────────────────────────────────────────────────────┐
│  Spreadsheet Intelligence          [Upload New File] │
├──────────────────┬──────────────────────────────────┤
│  Workbook Info   │  Ask a Question                  │
│                  │  ┌────────────────────────────┐  │
│  company_data    │  │ What was Q4 revenue in...  │  │
│                  │  └────────────────────────────┘  │
│  Sheets:         │                                  │
│  • Sales         │  [loading spinner via HTMX]      │
│  • Operations    │                                  │
│  • HR            │  ┌────────────────────────────┐  │
│                  │  │ Answer: $184,250            │  │
│  Sales columns:  │  │                            │  │
│  region          │  │ SQL:                       │  │
│  revenue         │  │ SELECT SUM(revenue)...     │  │
│  quarter         │  │                            │  │
│  ...             │  │ Source: Sales              │  │
│                  │  │ Columns: region, revenue   │  │
│                  │  │ Rows matched: 42           │  │
│                  │  └────────────────────────────┘  │
│                  │                                  │
│                  │  Previous Questions              │
│                  │  • Total headcount by dept?      │
│                  │  • Avg salary in Engineering?    │
└──────────────────┴──────────────────────────────────┘
```

---

## Build Phases

### Phase 1 — Core pipeline, no LLM (≈ 90 min)
- [ ] FastAPI app skeleton, config, database.py
- [ ] Workbook upload route + save to disk + Postgres record
- [ ] workbook_loader: pandas + openpyxl → DataFrames
- [ ] schema_profiler: sheet names, columns, dtypes, row count, samples
- [ ] DuckDB registry: register DataFrames
- [ ] Hardcoded test query runs against DuckDB — confirm exact answers
- [ ] Workbook show page with schema sidebar

**Goal:** Upload a file, see schema, prove DuckDB queries work correctly.

### Phase 2 — LLM query planner (≈ 90 min)
- [ ] Prompts: query_planner.txt with schema context
- [ ] query_planner.py: call Claude → return QueryPlan (Pydantic)
- [ ] query_executor.py: run QueryPlan SQL in DuckDB
- [ ] attribution_builder.py: extract sheet/column/row attribution
- [ ] Query route: POST /query → HTMX partial response
- [ ] answer_card.html partial: answer + SQL + attribution

**Goal:** Ask a natural language question, get exact answer with visible SQL.

### Phase 3 — Polish and product shape (≈ 60 min)
- [ ] Query history per workbook (query_log table + UI)
- [ ] Loading state (HTMX + spinner)
- [ ] Error handling: bad file, LLM failure, SQL error
- [ ] Accessibility: labels, focus states, aria-live for answer updates
- [ ] Formula cell warning if detected
- [ ] Row preview in answer card (optional)

### Phase 4 — README + wrap up (≈ 30 min)
- [ ] Setup instructions + .env.example
- [ ] Architecture overview (can reference this doc)
- [ ] Known limitations section
- [ ] Confirm test documents work end to end

---

## Known Limitations (for README)

- Assumes each sheet contains one primary rectangular table
- Column headers must be in the first non-empty row
- Formula cells use last cached Excel value — no live recalculation
- Ambiguous questions may produce incorrect SQL; review generated query
- Cross-sheet joins are inferred heuristically — works for obvious foreign keys
- Large files may be slow (no background processing in MVP)
- No authentication in MVP — single-user local app

---

## Future Growth Notes (leave as code comments)

- `workbook_loader.py`: multi-table detection within a single sheet
- `schema_profiler.py`: named range support, merged header handling
- `query_planner.py`: multi-step reasoning for complex questions
- `duckdb_registry.py`: async job for large file processing
- `workbooks.py` route: S3/cloud storage instead of local disk
- `main.py`: add auth layer (fastapi-users) + per-user workbook scoping
- `query_log`: saved/favorited queries, workbook sharing

---

## Environment Variables

```
DATABASE_URL=postgresql://localhost/spreadsheet_intelligence
ANTHROPIC_API_KEY=sk-...
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=50
```

---

## Test Documents

Located at: `/Users/brandongoodman/Desktop/aitakehome/AI Take Home XLSX/Test Documents/`
- `company_data.xlsx` — primary test file
- `testdata.xlsx` — secondary test file

Inspect these first before building schema profiler to understand real-world shape.
