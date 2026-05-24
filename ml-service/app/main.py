from contextlib import asynccontextmanager
import threading
import logging
from fastapi import FastAPI
from .kafka_service import kafka_consumer_loop
from .logging_config import setup_logging

logger = logging.getLogger(__name__)

consumer_thread = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global consumer_thread
    setup_logging()
    logger.info("Starting Sonara dev")
    consumer_thread = threading.Thread(target=kafka_consumer_loop, daemon=True)
    consumer_thread.start()
    logger.info("Kafka consumer started")
    yield
    logger.info("Shutting down")


app = FastAPI(title="Sonara dev", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": "Sonara dev"}


@app.get("/")
def root():
    return {"service": "Sonara dev", "version": "1.0", "mode": "worker"}