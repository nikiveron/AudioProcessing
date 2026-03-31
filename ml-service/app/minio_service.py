import time

from minio import Minio

from .config import (
    BUCKET,
    DOWNLOAD_RETRY_ATTEMPTS,
    DOWNLOAD_RETRY_DELAY,
    MINIO_ACCESS_KEY,
    MINIO_ENDPOINT,
    MINIO_SECRET_KEY,
    UPLOAD_RETRY_ATTEMPTS,
    UPLOAD_RETRY_DELAY,
)


def get_minio_client() -> Minio:
    """Create and return MinIO client instance"""
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )


def download_file(key: str) -> bytes:
    """Download file from MinIO with retry logic

    Args:
    ----
        key: Object key to download

    Returns:
    -------
        File content as bytes

    Raises:
    ------
        Exception: If download fails after all retries

    """
    last_error = None

    for attempt in range(DOWNLOAD_RETRY_ATTEMPTS):
        try:
            client = get_minio_client()
            response = client.get_object(BUCKET, key)
            data = response.read()
            response.close()
            print(f"[MinIO] Downloaded {key} (attempt {attempt + 1})")
            return data
        except Exception as e:
            last_error = e
            print(f"[MinIO] Download attempt {attempt + 1}/{DOWNLOAD_RETRY_ATTEMPTS} failed for {key}: {e}")
            if attempt < DOWNLOAD_RETRY_ATTEMPTS - 1:
                time.sleep(DOWNLOAD_RETRY_DELAY)

    raise Exception(f"Failed to download {key} after {DOWNLOAD_RETRY_ATTEMPTS} attempts: {last_error}")


def upload_file(key: str, file_stream, file_size: int) -> None:
    """Upload file to MinIO with retry logic

    Args:
    ----
        key: Object key for upload
        file_stream: File stream to upload
        file_size: Size of file in bytes

    Raises:
    ------
        Exception: If upload fails after all retries

    """
    last_error = None

    for attempt in range(UPLOAD_RETRY_ATTEMPTS):
        try:
            client = get_minio_client()
            file_stream.seek(0)
            client.put_object(
                BUCKET,
                key,
                file_stream,
                length=file_size,
                content_type="audio/wav",
            )
            print(f"[MinIO] Uploaded {key} (attempt {attempt + 1})")
            return
        except Exception as e:
            last_error = e
            print(f"[MinIO] Upload attempt {attempt + 1}/{UPLOAD_RETRY_ATTEMPTS} failed for {key}: {e}")
            if attempt < UPLOAD_RETRY_ATTEMPTS - 1:
                time.sleep(UPLOAD_RETRY_DELAY)

    raise Exception(f"Failed to upload {key} after {UPLOAD_RETRY_ATTEMPTS} attempts: {last_error}")
