import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.queue import router as queue_router
from api.sources import router as sources_router
from api.stories import router as stories_router
from db.database import init_db, seed_sources
from ingestion.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

app = FastAPI(title="Signal Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(queue_router)
app.include_router(stories_router)
app.include_router(sources_router)


def _run_startup():
    init_db()
    from db.database import get_db
    db = next(get_db())
    try:
        seed_sources(db)
    finally:
        db.close()
    start_scheduler()


@app.on_event("startup")
async def startup():
    _run_startup()


@app.on_event("shutdown")
async def shutdown():
    stop_scheduler()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/refresh")
def refresh():
    import threading
    from run import run
    threading.Thread(target=run, daemon=True).start()
    return {"status": "started"}
