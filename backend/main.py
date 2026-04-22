import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.queue import router as queue_router

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


@app.get("/health")
def health():
    return {"status": "ok"}
