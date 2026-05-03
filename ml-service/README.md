# SONARA - instrumental audio processor

Асинхронный Kafka worker для обработки аудиофайлов инструментов

МЛ-сервис для [приложения обработки аудио](https://github.com/nikiveron/AudioProcessing)

## Быстрый старт

```bash
docker-compose up -d
curl http://localhost:8000/health
```

## Архитектура обработки

```
Backend
  ↓ (Kafka job.prepared)
ML Service
  ├─ Скачать аудио из MinIO (inputKey)
  ├─ Обработать с выбранной моделью (keys/bass)
  ├─ Загрузить результат в MinIO (outputKey)
  ├─ Обновить Backend (PUT запрос)
  └─ Опубликовать результат (Kafka job.completed/job.failed)
```

## Входящее сообщение (Backend → ML Service)

**Topic:** `job.prepared`

```json
{
  "jobId": "550e8400-e29b-41d4-a716-446655440000",
  "inputKey": "uploads/input-12345.wav",
  "outputKey": "results/output-12345.wav",
  "parameters": {
    "instrument": 1,
    "genre": "default"
  }
}
```

**Параметры:**

- `jobId` - уникальный ID задачи
- `inputKey` - путь к исходному аудиофайлу в MinIO
- `outputKey` - путь для сохранения результата в MinIO
- `parameters.instrument` - enum инструмента (1=keys, 2=bass)
- `parameters.genre` - жанр для выбора конфигурации модели

## Обработка на ML Service

1. **Скачивание** - берет аудио из MinIO по `inputKey`
2. **Обработка** - использует соответствующую модель (keys или bass) из `parameters.instrument`
3. **Загрузка** - сохраняет результат в MinIO по `outputKey`
4. **Уведомление Backend** - PUT запрос: `{status: "Completed", outputKey: "..."}`
5. **Уведомление Kafka** - публикует в соответствующий topic

## Исходящие сообщения (ML Service → Backend)

**При успехе:**

- Topic: `job.completed`
- Message: `{"jobId": "xxx", "outputKey": "results/output-12345.wav"}`
- Backend PUT: `PUT /jobs/{jobId}` with `{status: "Completed", outputKey: "..."}`

**При ошибке:**

- Topic: `job.failed`
- Message: `{"jobId": "xxx", "error": "..."}`
- Backend PUT: `PUT /jobs/{jobId}` with `{status: "Failed", errorMessage: "..."}`

## Сервисы

- **ML Service:** http://localhost:8000 (/health, /)
- **MinIO Console:** http://localhost:9001 (minio/minio123)
- **Kafka:** localhost:9092

## Модели

- **Keys Model** - обрабатывает клавиши/пианино
- **Bass Model** - обрабатывает басс-гитару

Форматы поддерживаются: WAV, MP3 (определяется автоматически по расширению файла)
