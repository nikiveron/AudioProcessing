from fastapi import FastAPI
import torch
import json
import io
import requests
from confluent_kafka import Consumer, Producer
from minio import Minio
from model import GRUSeparator
from utils import process_single_file
from datetime import datetime

app = FastAPI(title="ML Audio Processor")

# ---------- CONFIG ----------

KAFKA_BOOTSTRAP = "kafka:9092"
INPUT_TOPIC = "job.prepared"
OUTPUT_TOPIC_OK = "job.completed"
OUTPUT_TOPIC_FAIL = "job.failed"

MINIO_ENDPOINT = "minio:9000"
MINIO_ACCESS_KEY = "minio"
MINIO_SECRET_KEY = "minio123"
BUCKET = "audio-files"

BACKEND_URL = "http://backend:8080/api/jobs"

# ---------- MODEL ----------

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = GRUSeparator().to(device)
model.load_state_dict(torch.load("model_weights.pth", map_location=device))
model.eval()

# ---------- MINIO ----------

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False,
)

# ---------- KAFKA ----------

consumer = Consumer({
    "bootstrap.servers": KAFKA_BOOTSTRAP,
    "group.id": "ml-service",
    "auto.offset.reset": "earliest",
})

producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP})

consumer.subscribe([INPUT_TOPIC])


# ---------- PROCESS FUNCTION ----------

def process_job(message):
    data = json.loads(message.value().decode())

    job_id = data["jobId"]
    input_key = data["inputKey"]
    output_key = data["outputKey"]

    try:
        print(f"Processing job {job_id}")

        # 🔹 1. Скачать файл из MinIO
        response = minio_client.get_object(BUCKET, input_key)
        input_bytes = response.read()

        # 🔹 2. ML обработка
        result_buf = process_single_file(model, input_bytes, device)
        result_buf.seek(0)

        # 🔹 3. Загрузить результат в MinIO
        minio_client.put_object(
            BUCKET,
            output_key,
            result_buf,
            length=-1,
            part_size=10 * 1024 * 1024,
            content_type="audio/wav",
        )

        # 🔹 4. Обновить статус Job
        requests.put(
            f"{BACKEND_URL}/{job_id}",
            json={
                "status": "Completed",
                "outputKey": output_key,
                "finishedAt": datetime.utcnow().isoformat()
            },
            timeout=10
        )

        # 🔹 5. Отправить Kafka событие
        producer.produce(
            OUTPUT_TOPIC_OK,
            json.dumps({
                "jobId": job_id,
                "outputKey": output_key
            }).encode()
        )
        producer.flush()

        print(f"Job {job_id} completed")

    except Exception as e:
        print(f"Job {job_id} failed: {e}")

        requests.put(
            f"{BACKEND_URL}/{job_id}",
            json={
                "status": "Failed",
                "finishedAt": datetime.utcnow().isoformat()
            },
            timeout=10
        )

        producer.produce(
            OUTPUT_TOPIC_FAIL,
            json.dumps({
                "jobId": job_id,
                "error": str(e)
            }).encode()
        )
        producer.flush()


# ---------- BACKGROUND LOOP ----------

@app.on_event("startup")
def start_consumer():
    import threading

    def loop():
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(msg.error())
                continue

            process_job(msg)

    threading.Thread(target=loop, daemon=True).start()


@app.get("/health")
def health():
    return {"status": "ok"}