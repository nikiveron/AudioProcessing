import os

# ===== Kafka Configuration =====
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
INPUT_TOPIC = os.getenv("INPUT_TOPIC", "job.prepared")
OUTPUT_TOPIC_OK = os.getenv("OUTPUT_TOPIC_OK", "job.completed")
OUTPUT_TOPIC_FAIL = os.getenv("OUTPUT_TOPIC_FAIL", "job.failed")

# Topics for backend compatibility
ALT_INPUT_TOPIC = os.getenv("ALT_INPUT_TOPIC", "audio-jobs")  # Alternative input topic

# ===== MinIO Configuration =====
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")
BUCKET = os.getenv("BUCKET", "audio-files")

# ===== Backend Configuration =====
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8080/api/jobs")
BACKEND_TIMEOUT = int(os.getenv("BACKEND_TIMEOUT", "10"))
BACKEND_MAX_RETRIES = int(os.getenv("BACKEND_MAX_RETRIES", "3"))

# ===== Model Configuration =====
MODEL_PATH = os.getenv("MODEL_PATH", "model_weights.pth")
DEVICE = os.getenv("DEVICE", "cuda")

# ===== Processing Configuration =====
DOWNLOAD_RETRY_ATTEMPTS = int(os.getenv("DOWNLOAD_RETRY_ATTEMPTS", "3"))
DOWNLOAD_RETRY_DELAY = int(os.getenv("DOWNLOAD_RETRY_DELAY", "2"))  # seconds
UPLOAD_RETRY_ATTEMPTS = int(os.getenv("UPLOAD_RETRY_ATTEMPTS", "3"))
UPLOAD_RETRY_DELAY = int(os.getenv("UPLOAD_RETRY_DELAY", "2"))  # seconds

# ===== Processing Parameters =====
# Valid genres and instruments
VALID_GENRES = ["Classic", "Jazz", "Rock", "pop", "classical", "jazz", "rock"]
VALID_INSTRUMENTS = ["Guitar", "Piano", "Vocal", "guitar", "piano", "vocal"]

# Processing mode flags
ENABLE_PARAMETER_PROCESSING = os.getenv("ENABLE_PARAMETER_PROCESSING", "true").lower() == "true"
DEFAULT_GENRE = os.getenv("DEFAULT_GENRE", "Classic")
DEFAULT_INSTRUMENT = os.getenv("DEFAULT_INSTRUMENT", "Guitar")

# ===== Logging Configuration =====
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
ENABLE_DEBUG = os.getenv("ENABLE_DEBUG", "false").lower() == "true"
