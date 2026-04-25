import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import audit, cleanup, export, sse, status, webhook
from app.services.redis_service import state
from app.services.worker import worker_loop


_worker_task: asyncio.Task | None = None


def worker_status() -> str:
    if _worker_task is None:
        return "not_started"
    if _worker_task.done():
        return "crashed"
    return "running"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _worker_task
    await state.connect()
    _worker_task = asyncio.create_task(worker_loop())
    yield
    _worker_task.cancel()
    await state.close()


app = FastAPI(title="CRM Heal", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(status.router)
app.include_router(cleanup.router)
app.include_router(sse.router)
app.include_router(audit.router)
app.include_router(export.router)
app.include_router(export.ghost_router)
app.include_router(webhook.router)
