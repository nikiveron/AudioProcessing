using AudioProcessing.Domain.Entities.Job;
using AudioProcessing.Infrastructure.Context;
using AudioProcessing.Infrastructure.Storage;
using Confluent.Kafka;
using System.Text.Json;

namespace AudioProcessing.Worker.Services;

public class JobConsumerService : BackgroundService
{
    private readonly ILogger<JobConsumerService> _logger;
    private readonly IConsumer<Null, string> _consumer;
    private readonly IProducer<Null, string> _producer;
    private readonly IServiceProvider _serviceProvider; 
    private readonly string _inputTopic = "job.created";
    private readonly string _outputTopic = "job.prepared";

    public JobConsumerService(ILogger<JobConsumerService> logger, IServiceProvider sp, IConfiguration cfg)
    {
        _logger = logger;
        _serviceProvider = sp;
        var consumerConfig = new ConsumerConfig
        {
            BootstrapServers = cfg["Kafka:BootstrapServers"],
            GroupId = "audio-workers-group",
            AutoOffsetReset = AutoOffsetReset.Earliest,
            EnableAutoCommit = false,

            SessionTimeoutMs = 60000,
            MaxPollIntervalMs = 300000,

            EnablePartitionEof = true,
            AllowAutoCreateTopics = true
        };

        var producerConfig = new ProducerConfig
        {
            BootstrapServers = cfg["Kafka:BootstrapServers"],
            EnableIdempotence = true,
            Acks = Acks.All
        };

        int retryCount = 0;
        const int maxRetries = 10;

        while (retryCount < maxRetries)
        {
            try
            {
                _consumer = new ConsumerBuilder<Null, string>(consumerConfig)
                    .SetErrorHandler((_, e) => _logger.LogError("Kafka error: {Reason}", e.Reason))
                    .SetLogHandler((_, log) => _logger.LogDebug("Kafka log: {Message}", log.Message))
                    .Build();

                _producer = new ProducerBuilder<Null, string>(producerConfig)
                    .SetErrorHandler((_, e) => _logger.LogError("Producer error: {Reason}", e.Reason))
                    .Build();

                _consumer.Subscribe(_inputTopic);
                // Небольшая пауза, чтобы consumer успел подключиться
                Thread.Sleep(1000);
                _logger.LogInformation("Worker connected to Kafka. Listening to {InputTopic}, will produce to {OutputTopic}", _inputTopic, _outputTopic);
                break;
            }
            catch (Exception ex)
            {
                retryCount++;
                _logger.LogWarning(ex, "Failed to connect to Kafka (attempt {RetryCount}/{MaxRetries}). Retrying in 5 seconds...", retryCount, maxRetries);

                if (retryCount >= maxRetries)
                {
                    _logger.LogError("Could not connect to Kafka after {MaxRetries} attempts", maxRetries);
                    throw;
                }

                Thread.Sleep(5000); // Ждем 5 секунд перед следующей попыткой
            }
        }
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                // Получаем сообщение из job.created
                var cr = _consumer.Consume(stoppingToken);

                // десереализация сообщения
                var payload = JsonSerializer.Deserialize<JsonElement>(cr.Message.Value);
                var jobId = Guid.Parse(payload.GetProperty("jobId").GetString());
                var inputKey = payload.GetProperty("inputKey").GetString();
                var outputKey = payload.GetProperty("outputKey").GetString();
                var parameters = payload.GetProperty("parameters");

                _logger.LogInformation("Worker received job {JobId} from {InputTopic}", jobId, _inputTopic);

                // новый DI-scope на каждую задачу для
                // DbContext корректно создавался и уничтожался
                // не было утечек соединений с БД
                using var scope = _serviceProvider.CreateScope();

                // получение сервисов
                var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
                var minio = scope.ServiceProvider.GetRequiredService<MinioService>();

                // обновление статуса задания
                JobEntity? job = await db.Jobs.FindAsync(jobId, stoppingToken);
                if (job == null)
                {
                    _logger.LogError("Job {JobId} not found in database", jobId);
                    _consumer.Commit(cr);
                    continue;
                }
                job.Status = JobStatus.Running; 
                job.StartedAt = DateTime.UtcNow;
                await db.SaveChangesAsync(stoppingToken);

                // Загрузка входного файла из MinIO в виде потока, без сохранения на диск.
                using var inStream = await minio.GetObjectStreamAsync(inputKey, stoppingToken);

                //==== ИМИТАЦИЯ ОБРАБОТКИ - ЗАМЕНИТЬ НА ВЫЗОВ ML-SERVICE ====
                var preparedKey = $"prepared/{jobId}.wav";
                using var outStream = new MemoryStream();
                await inStream.CopyToAsync(outStream, stoppingToken); // файл просто копируется
                outStream.Position = 0;
                var preparedMessage = new
                {
                    jobId = jobId,
                    preparedKey = preparedKey,
                    parameters = new
                    {
                        genre = parameters.GetProperty("genre").GetString(),
                        instrument = parameters.GetProperty("instrument").GetString()
                    }
                };
                var messageJson = JsonSerializer.Serialize(preparedMessage);
                await _producer.ProduceAsync(_outputTopic,
                    new Message<Null, string> { Value = messageJson },
                    stoppingToken);
                _logger.LogInformation("Worker published job {JobId} to {OutputTopic}", jobId, _outputTopic);
                job.Status = JobStatus.Success;
                await db.SaveChangesAsync(stoppingToken);
                // =============================================================

                // Подтверждаем исходное сообщение
                _consumer.Commit(cr);
            }
            catch (ConsumeException ex)
            {
                _logger.LogError(ex, "Error processing job");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error processing job");
            }
        }
    }

    /// <summary>
    /// Метод для корректного завершения. Consumer корректно закрывается, освобождаются ресурсы, offsets корректно сохраняются
    /// </summary>
    public override void Dispose()
    {
        _consumer.Close();
        _consumer.Dispose();
        base.Dispose();
    }
}

