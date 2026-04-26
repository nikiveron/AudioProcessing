# SONARA - instrumental audio processor

Асинхронный Kafka worker для обработки аудиофайлов с моделью GRU.

## Быстрый старт

```bash
docker-compose up -d
curl http://localhost:8000/health
```

## Архитектура

```
Kafka (job.prepared)
  ↓
ML Service (скачать → обработать → загрузить)
  ↓
Kafka (job.completed/failed)
```

1. Backend отправляет: `{"jobId": "xxx", "inputKey": "input/xxx.wav"}`
2. ML Service скачивает из MinIO, обрабатывает, загружает результат
3. Обновляет Backend через PUT и публикует результат в Kafka

## Сервисы

- ML Service: http://localhost:8000 (/health, /)
- MinIO Console: http://localhost:9001 (minio/minio123)
- Kafka: localhost:9092


## Backend интеграция

See: [BACKEND_INTEGRATION.md](BACKEND_INTEGRATION.md)
