import json
import time
import logging
import requests
from confluent_kafka import Consumer, Producer
from .config import (
    KAFKA_BOOTSTRAP,
    INPUT_TOPIC,
    OUTPUT_TOPIC_OK,
    OUTPUT_TOPIC_FAIL,
    BACKEND_URL,
    BACKEND_TIMEOUT,
)
from .minio_service import download_file, upload_file
from .model_manager import get_model_manager

logger = logging.getLogger(__name__)


def get_kafka_consumer():
    consumer = Consumer({
        "bootstrap.servers": KAFKA_BOOTSTRAP,
        "group.id": "ml-service",
        "auto.offset.reset": "earliest",
    })
    consumer.subscribe([INPUT_TOPIC])
    return consumer


def get_kafka_producer():
    return Producer({"bootstrap.servers": KAFKA_BOOTSTRAP})


def publish_result(job_id: str, output_key: str, success: bool, error_msg: str = None):
    producer = get_kafka_producer()
    topic = OUTPUT_TOPIC_OK if success else OUTPUT_TOPIC_FAIL
    
    message = {
        "JobId": job_id,
    }
    
    if success:
        message["OutputKey"] = output_key
    else:
        message["Error"] = error_msg
    
    producer.produce(
        topic,
        json.dumps(message).encode()
    )
    producer.flush()


def update_backend_job(job_id: str, status: str, output_key: str = None, error_msg: str = None):
    try:
        payload = {"status": status}
        if output_key:
            payload["OutputKey"] = output_key
        if error_msg:
            payload["ErrorMessage"] = error_msg
        
        requests.put(
            f"{BACKEND_URL}/{job_id}",
            json=payload,
            timeout=BACKEND_TIMEOUT
        )
        logger.info(f"Updated job {job_id} with status {status}")
    except Exception as e:
        logger.error(f"Error updating job {job_id}: {e}")


# Маппинг enum значений инструментов (backend отправляет enum: Piano, Bass, ElectroGuitar, AcousticGuitar)
INSTRUMENT_MAP = {
    "Piano": "keys",
    "Bass": "bass",
    "ElectroGuitar": "eg",
    "AcousticGuitar": "ag",
}


def process_job(message):
    data = json.loads(message.value().decode())
    job_id = data["JobId"]
    input_key = data["InputKey"]
    output_key = data["OutputKey"]
    
    parameters = data.get("parameters", {})
    raw_instrument = parameters.get("instrument", 1)
    instrument_id = INSTRUMENT_MAP.get(raw_instrument, "keys")
    output_ext = input_key.rsplit(".", 1)[-1] if "." in input_key else "wav"
    
    try:
        logger.info(f"Processing job {job_id} | Input: {input_key} | Output: {output_key}")
        
        logger.debug(f"Downloading {input_key}")
        input_bytes = download_file(input_key)
        logger.debug(f"Downloaded {len(input_bytes)} bytes")
        
        manager = get_model_manager()
        logger.info(f"Processing with '{instrument_id}' model")
        result_buf = manager.process_audio(instrument_id, input_bytes, output_format=output_ext.upper())
        result_buf.seek(0)
        result_bytes = result_buf.getvalue()
        logger.debug(f"Processing completed, output size: {len(result_bytes)} bytes")
        
        logger.debug(f"Uploading result to {output_key}")
        result_buf.seek(0)
        upload_file(output_key, result_buf, len(result_bytes))
        logger.debug("Upload completed")
        
        update_backend_job(job_id, "Completed", output_key=output_key)
        publish_result(job_id, output_key, success=True)
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        update_backend_job(job_id, "Failed", error_msg=str(e))
        publish_result(job_id, None, success=False, error_msg=str(e))


def kafka_consumer_loop():
    logger.info("Kafka consumer starting...")
    
    max_retries = 5
    retry_count = 0
    consumer = None
    
    while retry_count < max_retries:
        try:
            consumer = get_kafka_consumer()
            logger.info("Connected to Kafka")
            break
        except Exception as e:
            retry_count += 1
            logger.warning(f"Connection attempt {retry_count}/{max_retries} failed: {e}")
            time.sleep(5)
    
    if consumer is None:
        logger.error("Failed to connect to Kafka after all retries")
        return
    
    logger.info("Waiting for messages...")
    
    while True:
        try:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                logger.error(f"Kafka error: {msg.error()}")
                continue
            
            process_job(msg)
        except Exception as e:
            logger.error(f"Consumer loop error: {e}", exc_info=True)
            time.sleep(1)
