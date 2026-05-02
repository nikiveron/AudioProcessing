using AudioProcessing.Domain;
using AudioProcessing.Domain.DTOs.Job;
using AudioProcessing.Worker.Services.Interfaces;
using Confluent.Kafka;
using System.Text.Json;

namespace AudioProcessing.Worker.Services;

public class JobConsumerService : BackgroundService
{
    private readonly ILogger<JobConsumerService> _logger;
    private readonly IConsumer<Null, string> _consumer;
    private readonly IServiceScopeFactory _scopeFactory;

    public JobConsumerService(ILogger<JobConsumerService> logger, IServiceScopeFactory scopeFactory, IConfiguration cfg)
    {
        _scopeFactory = scopeFactory;
        _logger = logger;

        var config = new ConsumerConfig
        {
            BootstrapServers = cfg["Kafka:BootstrapServers"],
            GroupId = "audio-workers-group",
            AutoOffsetReset = AutoOffsetReset.Earliest,
            EnableAutoCommit = false
        };

        _consumer = new ConsumerBuilder<Null, string>(config).Build();
        _consumer.Subscribe(KafkaTopics.JobCreated);
    }

    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        _logger.LogInformation("Worker запущен успешно!");

        while (!ct.IsCancellationRequested)
        {
            try
            {
                var result = _consumer.Consume(ct);
                if (result?.Message?.Value is null)
                    continue;

                using var scope = _scopeFactory.CreateScope();
                var service = scope.ServiceProvider.GetRequiredService<IJobPreparationService>();

                var evt = JsonSerializer.Deserialize<JobCreatedEvent>(result.Message.Value)
                    ?? throw new InvalidOperationException("Не валидное сообщение из Kafka");
                await service.PrepareJobAsync(evt, ct);

                _consumer.Commit(result);
            }
            catch (ConsumeException ex)
            {
                _logger.LogError(ex, "Ошибка обработки job: ConsumeException");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Ошибка обработки job: Exception");
            }
        }
        _consumer.Close();
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

