from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import create_tables
from app.routes import workbooks, queries


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="Spreadsheet Intelligence", version="0.1.0", lifespan=lifespan)

# CORS — lock down allow_origins in production via ALLOWED_ORIGINS env var.
allowed_origins = ["*"] if settings.app_env == "development" else settings.allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workbooks.router)
app.include_router(queries.router)


@app.get("/health")
def health():
    return {"status": "ok"}
