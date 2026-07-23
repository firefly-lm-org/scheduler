"""FastAPI 入口：CORS + 路由挂载 + 后台任务 + 生命周期."""
import asyncio, logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from app.database import init_db
from app.routers import auth, node, task, admin
from app.services.background_tasks import background_scheduler_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

_bg_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bg_task
    logger.info("Firefly Scheduler v0.1 starting …")
    await init_db()
    _bg_task = asyncio.create_task(background_scheduler_loop())
    logger.info("Background scheduler started.")
    yield
    if _bg_task:
        _bg_task.cancel()
        try:
            await _bg_task
        except asyncio.CancelledError:
            pass
    logger.info("Firefly Scheduler shutting down.")


app = FastAPI(
    title="Firefly Scheduler",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(node.router, prefix="/api/v1")
app.include_router(task.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
