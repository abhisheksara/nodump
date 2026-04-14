"""AI Research Feed — FastAPI backend."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.chat import router as chat_router
from api.feed import router as feed_router
from api.feedback import router as feedback_router
from db.database import init_db
from ingestion.scheduler import run_ingestion, start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

app = FastAPI(title="AI Research Feed", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(feed_router)
app.include_router(feedback_router)
app.include_router(chat_router)


@app.on_event("startup")
async def startup():
    init_db()
    start_scheduler()
    # Kick off an initial ingestion run immediately in the background
    import threading
    threading.Thread(target=run_ingestion, daemon=True).start()


@app.on_event("shutdown")
async def shutdown():
    stop_scheduler()


@app.get("/health")
def health():
    return {"status": "ok"}
