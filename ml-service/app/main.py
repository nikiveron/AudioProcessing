from contextlib import asynccontextmanager
import threading
from fastapi import FastAPI
from .kafka_service import kafka_consumer_loop


consumer_thread = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global consumer_thread
    print("[App] Starting ML Audio Processor")
    consumer_thread = threading.Thread(target=kafka_consumer_loop, daemon=True)
    consumer_thread.start()
    print("[App] Kafka consumer started")
    yield
    print("[App] Shutting down")


app = FastAPI(title="ML Audio Processor", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": "ML Audio Processor"}


@app.get("/")
def root():
    return {"service": "ML Audio Processor", "version": "1.0", "mode": "worker"}
