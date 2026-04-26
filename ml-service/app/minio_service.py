import io
from minio import Minio
from .config import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, BUCKET


# Маппинг расширений файлов в MIME-типы
AUDIO_MIME_TYPES = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
    ".aiff": "audio/aiff",
    ".aac": "audio/aac",
    ".wma": "audio/x-ms-wma",
}


def get_content_type(filename: str) -> str:
    """
    Определяет MIME-тип по расширению файла.
    
    Args:
        filename: Имя файла (например, "audio.wav")
    
    Returns:
        MIME-тип (например, "audio/wav")
    """
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return AUDIO_MIME_TYPES.get(ext, "audio/wav")


def get_minio_client() -> Minio:
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )


def download_file(key: str) -> bytes:
    client = get_minio_client()
    response = client.get_object(BUCKET, key)
    data = response.read()
    response.close()
    return data


def upload_file(key: str, file_stream, file_size: int, content_type: str = None):
    """
    Загружает файл в MinIO.
    
    Args:
        key: Ключ (путь) в бакете
        file_stream: Поток с данными файла
        file_size: Размер файла в байтах
        content_type: MIME-тип файла (определяется автоматически если не указан)
    """
    client = get_minio_client()
    
    # Если content_type не указан, пытаемся определить по ключу
    if content_type is None:
        content_type = get_content_type(key)
    
    client.put_object(
        BUCKET,
        key,
        file_stream,
        length=file_size,
        content_type=content_type,
    )
