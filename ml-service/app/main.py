import threading
from contextlib import asynccontextmanager

from confluent_kafka import Consumer
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import KAFKA_BOOTSTRAP
from .kafka_service import kafka_consumer_loop
from .minio_service import get_minio_client

consumer_thread = None
shutdown_event = threading.Event()


def check_kafka_health() -> tuple[bool, str]:
    """Check Kafka connectivity"""
    try:
        consumer = Consumer({
            "bootstrap.servers": KAFKA_BOOTSTRAP,
            "group.id": "health-check",
            "session.timeout.ms": 3000,
        })
        consumer.list_topics(timeout=5)
        consumer.close()
        return True, "OK"
    except Exception as e:
        return False, str(e)


def check_minio_health() -> tuple[bool, str]:
    """Check MinIO connectivity"""
    try:
        client = get_minio_client()
        client.list_buckets()
        return True, "OK"
    except Exception as e:
        return False, str(e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global consumer_thread
    print("[App] Starting ML Audio Processor")

    # Start Kafka consumer in background thread
    consumer_thread = threading.Thread(target=kafka_consumer_loop, daemon=True)
    consumer_thread.start()
    print("[App] Kafka consumer started")

    yield

    print("[App] Shutting down")
    shutdown_event.set()
    if consumer_thread and consumer_thread.is_alive():
        consumer_thread.join(timeout=5)


app = FastAPI(
    title="ML Audio Processor",
    description="Asynchronous audio processing service with Kafka integration",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Basic health check endpoint"""
    return {
        "status": "ok",
        "service": "ML Audio Processor",
        "version": "1.0.0"
    }


@app.get("/health/detailed")
async def health_detailed():
    """Detailed health check including dependencies"""
    kafka_ok, kafka_msg = check_kafka_health()
    minio_ok, minio_msg = check_minio_health()

    overall_status = "healthy" if kafka_ok and minio_ok else "degraded"

    return {
        "status": overall_status,
        "service": "ML Audio Processor",
        "version": "1.0.0",
        "dependencies": {
            "kafka": {
                "status": "ok" if kafka_ok else "error",
                "message": kafka_msg
            },
            "minio": {
                "status": "ok" if minio_ok else "error",
                "message": minio_msg
            }
        },
        "consumer_thread": {
            "running": consumer_thread is not None and consumer_thread.is_alive(),
            "daemon": consumer_thread.daemon if consumer_thread else None
        }
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "ML Audio Processor",
        "version": "1.0.0",
        "mode": "worker",
        "endpoints": {
            "health": "/health",
            "health_detailed": "/health/detailed",
            "docs": "/docs"
        }
    }


@app.get("/info")
async def info():
    """Service information"""
    kafka_ok, _ = check_kafka_health()
    minio_ok, _ = check_minio_health()

    return {
        "name": "ML Audio Processor",
        "version": "1.0.0",
        "description": "Asynchronous audio processing with GRU model",
        "status": {
            "kafka_connected": kafka_ok,
            "minio_connected": minio_ok,
            "consumer_active": consumer_thread is not None and consumer_thread.is_alive()
        }
    }
