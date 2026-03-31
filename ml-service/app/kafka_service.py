import json
import time

import requests
from confluent_kafka import Consumer, KafkaError, Producer

from .config import (
    ALT_INPUT_TOPIC,
    BACKEND_MAX_RETRIES,
    BACKEND_TIMEOUT,
    BACKEND_URL,
    ENABLE_PARAMETER_PROCESSING,
    INPUT_TOPIC,
    KAFKA_BOOTSTRAP,
    OUTPUT_TOPIC_FAIL,
    OUTPUT_TOPIC_OK,
    VALID_GENRES,
    VALID_INSTRUMENTS,
)
from .minio_service import download_file, upload_file
from .model_service import process_audio_file


def get_kafka_consumer():
    """Create and return Kafka consumer subscribed to input topics"""
    consumer = Consumer({
        "bootstrap.servers": KAFKA_BOOTSTRAP,
        "group.id": "ml-service",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    })
    consumer.subscribe([INPUT_TOPIC, ALT_INPUT_TOPIC])
    print(f"[Kafka] Consumer subscribed to topics: {INPUT_TOPIC}, {ALT_INPUT_TOPIC}")
    return consumer


def get_kafka_producer():
    """Create and return Kafka producer"""
    return Producer({"bootstrap.servers": KAFKA_BOOTSTRAP})


def parse_job_message(message_dict):
    """Parse job message and extract parameters
    Args: message_dict: Parsed JSON message from Kafka
    Returns: Tuple of (job_id, input_key, genre, instrument)
    """
    job_id = message_dict.get("jobId")
    input_key = message_dict.get("inputKey")

    if not job_id or not input_key:
        raise ValueError("Missing required fields: jobId and inputKey")

    genre = None
    instrument = None

    if ENABLE_PARAMETER_PROCESSING:
        params = message_dict.get("parameters", {})
        if isinstance(params, dict):
            genre = params.get("Genre") or params.get("genre")
            instrument = params.get("Instrument") or params.get("instrument")

        if genre and genre not in VALID_GENRES:
            print(f"[Validation] Invalid genre: {genre}, ignoring")
            genre = None

        if instrument and instrument not in VALID_INSTRUMENTS:
            print(f"[Validation] Invalid instrument: {instrument}, ignoring")
            instrument = None

    return job_id, input_key, genre, instrument


def publish_result(job_id: str, output_key: str = None, success: bool = True, error_msg: str = None):
    """Publish job result to Kafka

    Args:
    ----
        job_id: Job identifier
        output_key: S3/MinIO path to output file (if successful)
        success: Whether processing was successful
        error_msg: Error message (if failed)

    """
    try:
        producer = get_kafka_producer()
        topic = OUTPUT_TOPIC_OK if success else OUTPUT_TOPIC_FAIL

        message = {
            "jobId": job_id,
        }

        if success and output_key:
            message["outputKey"] = output_key
        elif not success and error_msg:
            message["error"] = error_msg

        producer.produce(
            topic,
            value=json.dumps(message).encode(),
            key=job_id.encode()
        )
        producer.flush()
        print(f"[Kafka] Published result to {topic} for job {job_id}")
    except Exception as e:
        print(f"[Kafka] Error publishing result: {e}")


def update_backend_job(job_id: str, status: str, output_key: str = None, error_msg: str = None):
    """Update backend job status with retry logic

    Args:
    ----
        job_id: Job identifier
        status: Job status (Completed, Failed, etc.)
        output_key: S3/MinIO path to output file (if successful)
        error_msg: Error message (if failed)

    """
    payload = {"status": status}
    if output_key:
        payload["outputKey"] = output_key
    if error_msg:
        payload["errorMessage"] = error_msg

    last_error = None

    for attempt in range(BACKEND_MAX_RETRIES):
        try:
            response = requests.put(
                f"{BACKEND_URL}/{job_id}",
                json=payload,
                timeout=BACKEND_TIMEOUT
            )
            if response.status_code in [200, 204]:
                print(f"[Backend] Updated job {job_id} with status {status}")
                return
            else:
                last_error = f"HTTP {response.status_code}: {response.text}"
                print(f"[Backend] Attempt {attempt + 1}/{BACKEND_MAX_RETRIES} failed: {last_error}")
        except requests.RequestException as e:
            last_error = str(e)
            print(f"[Backend] Attempt {attempt + 1}/{BACKEND_MAX_RETRIES} failed: {last_error}")

        if attempt < BACKEND_MAX_RETRIES - 1:
            time.sleep(1)

    print(f"[Backend] Failed to update job {job_id} after {BACKEND_MAX_RETRIES} attempts: {last_error}")


def process_job(message):
    """Process job message: download, process, upload, and notify
    Args: message: Kafka message object
    """
    try:
        message_data = json.loads(message.value().decode())
        job_id, input_key, genre, instrument = parse_job_message(message_data)

        output_key = f"output/{job_id}.wav"

        print(f"[Job] Processing job {job_id}")
        if genre:
            print(f"[Job] Genre: {genre}")
        if instrument:
            print(f"[Job] Instrument: {instrument}")

        print(f"[Download] Downloading {input_key}")
        input_bytes = download_file(input_key)
        print(f"[Download] Downloaded {len(input_bytes)} bytes")

        print("[ML] Processing with model")
        result_buf = process_audio_file(input_bytes, genre=genre, instrument=instrument)
        result_buf.seek(0)
        result_bytes = result_buf.getvalue()
        print(f"[ML] Processing completed, output size: {len(result_bytes)} bytes")

        print(f"[Upload] Uploading result to {output_key}")
        result_buf.seek(0)
        upload_file(output_key, result_buf, len(result_bytes))
        print("[Upload] Uploaded successfully")

        update_backend_job(job_id, "Completed", output_key=output_key)
        publish_result(job_id, output_key=output_key, success=True)
        print(f"[Success] Job {job_id} completed successfully")

    except ValueError as e:
        print(f"[Error] Message parsing error: {e}")
    except Exception as e:
        job_id = message_data.get("jobId", "unknown")
        print(f"[Error] Job {job_id} failed: {e}")
        update_backend_job(job_id, "Failed", error_msg=str(e))
        publish_result(job_id, success=False, error_msg=str(e))


def kafka_consumer_loop():
    """Main Kafka consumer loop"""
    print("[Consumer] Starting Kafka consumer loop...")

    max_retries = 5
    retry_count = 0
    consumer = None

    while retry_count < max_retries:
        try:
            consumer = get_kafka_consumer()
            print("[Consumer] Successfully connected to Kafka")
            break
        except Exception as e:
            retry_count += 1
            print(f"[Consumer] Connection attempt {retry_count}/{max_retries} failed: {e}")
            if retry_count < max_retries:
                time.sleep(5)

    if consumer is None:
        print("[Consumer] Failed to connect to Kafka after all retries")
        return

    print("[Consumer] Ready to process messages")
    while True:
        try:
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(f"[Consumer] Kafka error: {msg.error()}")
                    continue

            print(f"[Consumer] Received message from topic {msg.topic()}")
            process_job(msg)

        except Exception as e:
            print(f"[Consumer] Unexpected error in loop: {e}")
            time.sleep(1)
        except KeyboardInterrupt:
            print("[Consumer] Shutdown requested")
            break

    consumer.close()
