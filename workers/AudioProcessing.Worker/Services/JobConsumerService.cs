using AudioProcessing.Domain;
using AudioProcessing.Domain.DTOs.Job;
using AudioProcessing.Domain.Exceptions;
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

    protected override async Task ExecuteAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("Worker запущен успешно!");

        while (!cancellationToken.IsCancellationRequested)
        {
            JobCreatedEvent? currentJob = null;
            try
            {
                var result = _consumer.Consume(cancellationToken);
                if (result?.Message?.Value is null)
                    continue;

                using var scope = _scopeFactory.CreateScope();
                var service = scope.ServiceProvider.GetRequiredService<IJobPreparationService>();

                var evt = JsonSerializer.Deserialize<JobCreatedEvent>(result.Message.Value)
                    ?? throw new InvalidOperationException("Не валидное сообщение из Kafka");

                currentJob = evt;

                await service.PrepareJobAsync(evt, cancellationToken);

                _consumer.Commit(result);
            }
            catch (ConsumeException ex)
            {
                _logger.LogError("Ошибка обработки job: ConsumeException: {ex}", ex);
                await PublishFailureEvent(currentJob, ex.Message, cancellationToken);
            }
            catch (HttpErrorException ex)
            {
                _logger.LogError("Ошибка! {Error}", ex.ErrorMessage);
                await PublishFailureEvent(currentJob, ex.ErrorMessage, cancellationToken);
            }
            catch (Exception ex)
            {
                _logger.LogError("Ошибка обработки job: Exception: {ex}", ex);
                await PublishFailureEvent(currentJob, ex.Message, cancellationToken);
            }
        }
    }

    private async Task PublishFailureEvent(JobCreatedEvent? job, string errorMessage, CancellationToken ct)
    {
        try
        {
            using var scope = _scopeFactory.CreateScope();
            var publisher = scope.ServiceProvider.GetRequiredService<IKafkaPublisher>();

            var failureEvent = new JobStatusEvent(
                JobId: job == null ? Guid.Empty : job.JobId,
                OutputKey: job == null ? string.Empty : job.OutputKey,
                Error: errorMessage
            );

            await publisher.ProduceFailed(failureEvent, ct);
            _logger.LogInformation("Failure event опубликован в Kafka");
        }
        catch (Exception pubEx)
        {
            _logger.LogError(pubEx, "Ошибка публикации ивента в Kafka");
        }
    }

    public override void Dispose()
    {
        try
        {
            _consumer.Close();
        }
        catch (ObjectDisposedException)
        {
        }
        _consumer.Dispose();
        base.Dispose();
    }
}

