from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import get_conn, pool
from .routers import auth, catalog, services, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open()
    yield
    pool.close()


app = FastAPI(
    title="Turismo GT - API de servicios de IA",
    description="API REST con chatbot RAG y agentes de IA para turismo en Guatemala.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(catalog.router)
app.include_router(services.router)


@app.get("/health", tags=["Sistema"])
def health(conn=Depends(get_conn)):
    row = conn.execute("SELECT count(*) AS n FROM ai_services").fetchone()
    return {"status": "ok", "ai_services": row["n"]}