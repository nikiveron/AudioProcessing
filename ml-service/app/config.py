import os

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
INPUT_TOPIC = os.getenv("INPUT_TOPIC", "job.prepared")
OUTPUT_TOPIC_OK = os.getenv("OUTPUT_TOPIC_OK", "job.completed")
OUTPUT_TOPIC_FAIL = os.getenv("OUTPUT_TOPIC_FAIL", "job.failed")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")
BUCKET = os.getenv("BUCKET", "audio-files")

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8080/api/jobs")
BACKEND_TIMEOUT = int(os.getenv("BACKEND_TIMEOUT", "10"))

MODEL_PATH = os.getenv("MODEL_PATH", "model_weights.pth")
DEVICE = os.getenv("DEVICE", "cuda")
