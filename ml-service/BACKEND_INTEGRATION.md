## Backend Integration

### ML Service Capabilities

ML-сервис поддерживает обработку аудио с параметрами и отправляет результаты обратно в Backend.

### Message Flow

```
Backend → Kafka (job.prepared or audio-jobs)
           ↓
ML Service:
  - Скачивает файл из MinIO
  - Обрабатывает с учетом параметров (Genre, Instrument)
  - Загружает результат в MinIO
  - Обновляет Backend через PUT API
  - Публикует результат в Kafka (job.completed/job.failed)
           ↓
Backend ← Kafka
```

### 1. Input Topics

ML-сервис слушает оба topic'а:

- **Primary**: `job.prepared` (по спецификации)
- **Alternative**: `audio-jobs` (текущий topic от Backend)

Это обеспечивает совместимость.

### 2. Input Message Format

Backend отправляет в Kafka:

```json
{
  "jobId": "550e8400-e29b-41d4-a716-446655440000",
  "inputKey": "input/550e8400-e29b-41d4-a716-446655440000.wav",
  "outputKey": "results/550e8400-e29b-41d4-a716-446655440000_filename.wav",
  "parameters": {
    "Genre": "Classic",
    "Instrument": "Guitar"
  }
}
```

**Обязательные поля**:

- `jobId` (string UUID)
- `inputKey` (string S3/MinIO path)

**Опциональные поля**:

- `outputKey` (string) - Игнорируется ML-сервисом, генерирует свой: `output/{jobId}.wav`
- `parameters` (object):
  - `Genre` (string): Classic, Jazz, Rock (case-insensitive)
  - `Instrument` (string): Guitar, Piano, Vocal (case-insensitive)

### 3. ML Service Processing

#### Параме распознавание

- Жанры: Classic, Jazz, Rock (и case-insensitive варианты)
- Инструменты: Guitar, Piano, Vocal

#### Применяемые эффекты

**Жанры**:

- Classic: Усиление среднего диапазона (500-4000Hz)
- Jazz: Мягкое сжатие и легкий boost
- Rock: Усиление высоких частот (>3000Hz) + дополнительная громкость

**Инструменты**:

- Guitar: Усиление среднего диапазона (300-3000Hz)
- Piano: Сохранение динамики, чистые высокие частоты
- Vocal: Усиление диапазона присутствия (2-4kHz)

#### Output

- **Успешно**: Файл загружается в `output/{jobId}.wav`
- **Ошибка**: Backend получит сообщение об ошибке

### 4. Update Backend Endpoint

ML-сервис обновляет Backend через PUT запрос:

```
PUT /api/jobs/{jobId}
```

**Request body**:

```json
{
  "status": "Completed",
  "outputKey": "output/550e8400-e29b-41d4-a716-446655440000.wav"
}
```

или при ошибке:

```json
{
  "status": "Failed",
  "errorMessage": "Failed to download input file: connection timeout"
}
```

**Параметры**:

- `status` (string): "Completed", "Failed"
- `outputKey` (string, optional): S3/MinIO path к обработанному файлу
- `errorMessage` (string, optional): Сообщение об ошибке

**Retry логика**:

- До 3 попыток обновления Backend
- Задержка между попытками: 1 секунда

### 5. Output Topics

ML-сервис публикует результаты в Kafka:

#### Success: `job.completed`

```json
{
  "jobId": "550e8400-e29b-41d4-a716-446655440000",
  "outputKey": "output/550e8400-e29b-41d4-a716-446655440000.wav"
}
```

#### Failure: `job.failed`

```json
{
  "jobId": "550e8400-e29b-41d4-a716-446655440000",
  "error": "Failed to download input file: connection timeout"
}
```

### 6. Backend Requirements

Для полной интеграции Backend должен:

1. **Отправлять в Kafka** сообщения с:
   - jobId и inputKey (обязательно)
   - Параметры Genre/Instrument (опционально)

2. **Иметь PUT endpoint** `/api/jobs/{jobId}` для обновления статуса

3. **Слушать Kafka topics** (опционально, но рекомендуется):
   - job.completed
   - job.failed

4. **Хранить файлы в MinIO** с правильных путям:
   - Input: `input/{jobId}.wav`
   - Output будет в: `output/{jobId}.wav`

### 7. Конфигурация ML-сервиса

Переменные окружения для настройки интеграции:

```bash
# Kafka
KAFKA_BOOTSTRAP=kafka:9092
INPUT_TOPIC=job.prepared
ALT_INPUT_TOPIC=audio-jobs
OUTPUT_TOPIC_OK=job.completed
OUTPUT_TOPIC_FAIL=job.failed

# Backend
BACKEND_URL=http://backend:8080/api/jobs
BACKEND_TIMEOUT=10
BACKEND_MAX_RETRIES=3

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minio
MINIO_SECRET_KEY=minio123
BUCKET=audio-files

# Processing
ENABLE_PARAMETER_PROCESSING=true
DOWNLOAD_RETRY_ATTEMPTS=3
DOWNLOAD_RETRY_DELAY=2
UPLOAD_RETRY_ATTEMPTS=3
UPLOAD_RETRY_DELAY=2
```

### 8. Health Checks

Backend может проверять статус ML-сервиса:

```bash
GET /health
Response: {"status": "ok", "service": "ML Audio Processor"}

GET /health/detailed
Response: Детальная информация о зависимостях (Kafka, MinIO)

GET /info
Response: Информация о сервисе и компонентах
```

### 9. Пример workflow

```bash
# 1. Backend загружает файл в MinIO
PUT /api/minIO/input/job-123.wav

# 2. Backend создает Job в БД
POST /api/jobs
Response: {jobId: "job-123", ...}

# 3. Backend отправляет сообщение в Kafka
{
  "jobId": "job-123",
  "inputKey": "input/job-123.wav",
  "parameters": {
    "Genre": "Jazz",
    "Instrument": "Piano"
  }
}

# 4. ML-сервис получает сообщение и обрабатывает:
# - Скачивает input/job-123.wav
# - Применяет Jazz+Piano эффекты
# - Загружает output/job-123.wav

# 5. ML-сервис обновляет Backend:
PUT /api/jobs/job-123
{
  "status": "Completed",
  "outputKey": "output/job-123.wav"
}

# 6. ML-сервис публикует результат:
Kafka: job.completed
{
  "jobId": "job-123",
  "outputKey": "output/job-123.wav"
}

# 7. Frontend скачивает результат:
GET /api/jobs/job-123/download
```

### 10. Error Handling

ML-сервис обрабатывает ошибки:

- **MinIO ошибки**: Retry с экспоненциальной задержкой
- **Обработка аудио**: Отправляет ошибку в errorMessage
- **Backend недоступен**: Логирует, но продолжает работать
- **Kafka ошибки**: Reconn попытки с экспоненциальной задержкой

Все ошибки логируются детально для отладки.

### 11. Monitoring & Debugging

```bash
# Проверить логи ML-сервиса
docker logs audio_ml_service

# Проверить статус
curl http://localhost:8000/health/detailed

# Проверить Kafka messages
docker exec kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic job.completed

# Проверить MinIO files
docker exec minio s3cmd ls s3://audio-files/
```

```csharp
public class KafkaConsumerService : BackgroundService
{
    private readonly IServiceProvider _serviceProvider;

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var config = new ConsumerConfig
        {
            BootstrapServers = "kafka:9092",
            GroupId = "backend-service",
            AutoOffsetReset = AutoOffsetReset.Earliest
        };

        using (var consumer = new ConsumerBuilder<string, string>(config).Build())
        {
            consumer.Subscribe(new[] { "job.completed", "job.failed" });

            while (!stoppingToken.IsCancellationRequested)
            {
                var result = consumer.Consume(stoppingToken);

                using (var scope = _serviceProvider.CreateScope())
                {
                    var db = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();

                    if (result.Topic == "job.completed")
                    {
                        var data = JsonSerializer.Deserialize<JobCompletedMessage>(result.Message.Value);
                        var job = await db.Jobs.FindAsync(Guid.Parse(data.JobId));
                        if (job != null)
                        {
                            job.Status = "Completed";
                            job.OutputKey = data.OutputKey;
                            job.FinishedAt = DateTime.UtcNow;
                            await db.SaveChangesAsync();
                        }
                    }
                    else if (result.Topic == "job.failed")
                    {
                        var data = JsonSerializer.Deserialize<JobFailedMessage>(result.Message.Value);
                        var job = await db.Jobs.FindAsync(Guid.Parse(data.JobId));
                        if (job != null)
                        {
                            job.Status = "Failed";
                            job.ErrorMessage = data.Error;
                            job.FinishedAt = DateTime.UtcNow;
                            await db.SaveChangesAsync();
                        }
                    }
                }
            }
        }
    }
}

public class JobCompletedMessage { public string JobId { get; set; } public string OutputKey { get; set; } }
public class JobFailedMessage { public string JobId { get; set; } public string Error { get; set; } }
```

### 4. Download Endpoint

```csharp
[HttpGet("{id:guid}/download")]
public async Task<IActionResult> DownloadAsync(Guid id)
{
    var job = await _context.Jobs.FindAsync(id);
    if (job == null || string.IsNullOrEmpty(job.OutputKey))
        return NotFound();

    var stream = new MemoryStream();
    await minioClient.GetObjectAsync(new GetObjectArgs()
        .WithBucket("audio-files")
        .WithObject(job.OutputKey)
        .WithCallbackStream(async (s) => await s.CopyToAsync(stream)));

    stream.Seek(0);
    return File(stream, "audio/wav", $"output-{id}.wav");
}
```

### 5. Dependency Injection (Program.cs)

```csharp
services.AddSingleton<MinioClient>(_ => new MinioClient()
    .WithEndpoint("minio:9000")
    .WithCredentials("minio", "minio123")
    .Build());

services.AddSingleton<IProducer<string, string>>(_ =>
    new ProducerBuilder<string, string>(
        new ProducerConfig { BootstrapServers = "kafka:9092" })
    .Build());

services.AddHostedService<KafkaConsumerService>();
```

### 6. Message Format

Backend sends to Kafka topic `job.prepared`:

```json
{
  "jobId": "550e8400-e29b-41d4-a716-446655440000",
  "inputKey": "input/job-550e8400-e29b-41d4-a716-446655440000.wav"
}
```

ML Service sends to `job.completed`:

```json
{
  "jobId": "550e8400-e29b-41d4-a716-446655440000",
  "outputKey": "output/550e8400-e29b-41d4-a716-446655440000.wav"
}
```

Or `job.failed`:

```json
{
  "jobId": "550e8400-e29b-41d4-a716-446655440000",
  "error": "Failed to download from MinIO"
}
```

### Nuget Dependencies

```
Minio
Confluent.Kafka
```

public class JobFailedMessage
{
public string JobId { get; set; }
public string Error { get; set; }
}

````

---

## 3️⃣ PUT Endpoint для обновления Job

ML Service будет делать PUT запрос к этому endpoint'у:

```csharp
[HttpPut("{id:guid}")]
[ProducesResponseType(StatusCodes.Status200OK)]
[ProducesResponseType(StatusCodes.Status404NotFound)]
[ProducesResponseType(StatusCodes.Status400BadRequest)]
public async Task<IActionResult> UpdateJob(
    Guid id,
    [FromBody] UpdateJobRequest request
)
{
    var job = await _context.Jobs.FindAsync(id);

    if (job == null)
        return NotFound($"Job {id} not found");

    // Обновить поля
    if (!string.IsNullOrEmpty(request.Status))
        job.Status = request.Status;

    if (!string.IsNullOrEmpty(request.OutputKey))
        job.OutputKey = request.OutputKey;

    if (request.StartedAt.HasValue)
        job.StartedAt = request.StartedAt.Value;

    if (request.FinishedAt.HasValue)
        job.FinishedAt = request.FinishedAt.Value;

    job.UpdatedAt = DateTime.UtcNow;

    _context.Jobs.Update(job);
    await _context.SaveChangesAsync();

    return Ok(job);
}

public class UpdateJobRequest
{
    public string Status { get; set; }
    public string OutputKey { get; set; }
    public DateTime? StartedAt { get; set; }
    public DateTime? FinishedAt { get; set; }
}
````

---

## 4️⃣ GET Endpoint для скачивания результата

Когда пользователь захочет скачать обработанный файл:

```csharp
[HttpGet("{id:guid}/download")]
public async Task<IActionResult> DownloadResult(Guid id)
{
    var job = await _context.Jobs.FindAsync(id);

    if (job == null)
        return NotFound();

    if (string.IsNullOrEmpty(job.OutputKey))
        return BadRequest("Job not completed yet");

    // Скачать файл из MinIO
    var minioClient = new MinioClient()
        .WithEndpoint("minio:9000")
        .WithCredentials("minio", "minio123")
        .Build();

    try
    {
        var stream = new MemoryStream();

        var getArgs = new GetObjectArgs()
            .WithBucket("audio-files")
            .WithObject(job.OutputKey)
            .WithCallbackStream(async (s) => await s.CopyToAsync(stream));

        await minioClient.GetObjectAsync(getArgs);

        stream.Position = 0;

        return File(
            stream,
            "audio/wav",
            $"output-{job.Id}.wav"
        );
    }
    catch (Exception ex)
    {
        return StatusCode(500, ex.Message);
    }
}
```

---

## 5️⃣ Job модель в БД

```csharp
public class Job
{
    public Guid Id { get; set; }

    public string Status { get; set; } // Queued, Processing, Completed, Failed

    public string InputKey { get; set; }   // input/job-xxx.wav

    public string OutputKey { get; set; }  // output/job-xxx.wav

    public string ErrorMessage { get; set; }

    public DateTime CreatedAt { get; set; }

    public DateTime UpdatedAt { get; set; }

    public DateTime? StartedAt { get; set; }

    public DateTime? FinishedAt { get; set; }
}
```

---

## 6️⃣ Миграция Entity Framework

```csharp
modelBuilder.Entity<Job>(entity =>
{
    entity.HasKey(e => e.Id);

    entity.Property(e => e.Status)
        .IsRequired()
        .HasMaxLength(50);

    entity.Property(e => e.InputKey)
        .IsRequired()
        .HasMaxLength(500);

    entity.Property(e => e.OutputKey)
        .HasMaxLength(500);

    entity.Property(e => e.ErrorMessage)
        .HasMaxLength(1000);

    entity.HasIndex(e => e.Status);
    entity.HasIndex(e => e.CreatedAt);
});
```

---

## 7️⃣ Dependency Injection в Startup

```csharp
services.AddSingleton<IProducer<string, string>>(sp =>
{
    var config = new ProducerConfig { BootstrapServers = "kafka:9092" };
    return new ProducerBuilder<string, string>(config).Build();
});

services.AddSingleton<MinioClient>(sp =>
{
    return new MinioClient()
        .WithEndpoint("minio:9000")
        .WithCredentials("minio", "minio123")
        .Build();
});

// Запустить Kafka consumer в background
services.AddHostedService<KafkaConsumerService>();
```

---

## 8️⃣ Background Service для слушания Kafka

```csharp
public class KafkaConsumerService : BackgroundService
{
    private readonly ILogger<KafkaConsumerService> _logger;
    private readonly IServiceProvider _serviceProvider;

    public KafkaConsumerService(
        ILogger<KafkaConsumerService> logger,
        IServiceProvider serviceProvider
    )
    {
        _logger = logger;
        _serviceProvider = serviceProvider;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var config = new ConsumerConfig
        {
            BootstrapServers = "kafka:9092",
            GroupId = "backend-service",
            AutoOffsetReset = AutoOffsetReset.Earliest,
        };

        using (var consumer = new ConsumerBuilder<string, string>(config).Build())
        {
            consumer.Subscribe(new[] { "job.completed", "job.failed" });

            while (!stoppingToken.IsCancellationRequested)
            {
                try
                {
                    var consumeResult = consumer.Consume(stoppingToken);

                    using (var scope = _serviceProvider.CreateScope())
                    {
                        var dbContext = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();

                        if (consumeResult.Topic == "job.completed")
                        {
                            var data = JsonSerializer.Deserialize<JobCompletedMessage>(
                                consumeResult.Message.Value
                            );

                            var job = await dbContext.Jobs.FindAsync(Guid.Parse(data.JobId));
                            if (job != null)
                            {
                                job.Status = "Completed";
                                job.OutputKey = data.OutputKey;
                                job.FinishedAt = DateTime.UtcNow;
                                await dbContext.SaveChangesAsync();

                                _logger.LogInformation($"Job {data.JobId} completed");
                            }
                        }
                        else if (consumeResult.Topic == "job.failed")
                        {
                            var data = JsonSerializer.Deserialize<JobFailedMessage>(
                                consumeResult.Message.Value
                            );

                            var job = await dbContext.Jobs.FindAsync(Guid.Parse(data.JobId));
                            if (job != null)
                            {
                                job.Status = "Failed";
                                job.ErrorMessage = data.Error;
                                job.FinishedAt = DateTime.UtcNow;
                                await dbContext.SaveChangesAsync();

                                _logger.LogError($"Job {data.JobId} failed: {data.Error}");
                            }
                        }
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, "Error processing Kafka message");
                }
            }
        }
    }
}
```

---

## ✅ Checklist для интеграции

- [ ] Установлены NuGet пакеты: `Minio`, `Confluent.Kafka`
- [ ] Добавлена Job модель в БД
- [ ] Создана миграция для таблицы Jobs
- [ ] Реализован POST endpoint для загрузки файла
- [ ] Реализован PUT endpoint `/api/jobs/{id}` для обновления статуса
- [ ] Реализован GET endpoint для скачивания результата
- [ ] Настроен Kafka Consumer в BackgroundService
- [ ] Конфигурация Kafka и MinIO в appsettings.json
- [ ] Протестирована整합 с ML Service

---

**Готово! Backend теперь полностью интегрирован с ML Service архитектурой.**
