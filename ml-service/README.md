# ML Audio Processor

Асинхронный Kafka worker для обработки аудиофайлов с моделью GRU. Поддерживает параметровую обработку по жанру и инструменту.

## ⚡ Быстрый старт

### Docker (рекомендуется)

```bash
docker-compose up -d
curl http://localhost:8000/health
```

### Локально с Poetry

```bash
# Установить зависимости
poetry install

# Запустить сервис
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Windows

```bash
# Запустить setup скрипт
setup.bat

# Или вручную
poetry install
poetry run uvicorn app.main:app --reload
```

## Архитектура

```
Kafka (job.prepared или audio-jobs)
  ↓
ML Service (скачать → обработать → загрузить)
  ↓
Kafka (job.completed/failed) + PUT Backend API
```

1. Backend отправляет: `{"jobId": "xxx", "inputKey": "input/xxx.wav", "parameters": {...}}`
2. ML Service скачивает из MinIO, обрабатывает, загружает результат
3. Обновляет Backend через PUT и публикует результат в Kafka

## Сервисы

- ML Service: http://localhost:8000 (/health, /health/detailed, /info, /docs)
- MinIO Console: http://localhost:9001 (minio/minio123)
- Kafka: localhost:9092

## Структура

```
app/
  main.py           - FastAPI (endpoints, lifespan, health checks)
  config.py         - Переменные окружения, конфигурация
  kafka_service.py  - Consumer/producer логика с параметрами
  minio_service.py  - Download/upload с retry логикой
  model_service.py  - Загрузка модели, обработка с параметрами
  model.py          - GRU архитектура
  utils.py          - Утилиты аудио, жанр/инструмент эффекты
```

### Поддерживаемые параметры:

**Жанры:** Classic, Jazz, Rock (case-insensitive)
**Инструменты:** Electro Guitar

## Endpoints

### Health Check

```
GET /health
Response: {"status": "ok", "service": "ML Audio Processor"}

GET /health/detailed
Response: Детальная информация о зависимостях (Kafka, MinIO)
```

### Info

```
GET /info
Response: Информация о сервисе и статусе компонентов

GET /
Response: Базовая информация о сервисе
```

### API Documentation

```
GET /docs         - Swagger UI
GET /redoc        - ReDoc
```

## Backend Integration

See: [BACKEND_INTEGRATION.md](BACKEND_INTEGRATION.md)

## Разработка

### С Poetry

poetry install

# Запуск
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Или активировать shell
poetry shell
uvicorn app.main:app --reload
```

### Linting & Formatting

```bash
# Проверка кода (Ruff)
poetry run ruff check 

# Автоматическое исправление
poetry run ruff check --fix

# Или одной командой
make format lint-fix
```