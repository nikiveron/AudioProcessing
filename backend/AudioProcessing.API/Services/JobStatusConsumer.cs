using AudioProcessing.API.Services.Interfaces;
using AudioProcessing.Domain;
using AudioProcessing.Domain.DTOs.Job;
using Confluent.Kafka;
using System.Text.Json;

namespace AudioProcessing.API.Services;

public class JobStatusConsumer : BackgroundService
{
    private readonly ILogger<JobStatusConsumer> _logger;
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly IConsumer<Null, string> _consumer;

    public JobStatusConsumer(
        ILogger<JobStatusConsumer> logger,
        IConfiguration cfg,
        IServiceScopeFactory scopeFactory)
    {
        _logger = logger;
        _scopeFactory = scopeFactory;

        var config = new ConsumerConfig
        {
            BootstrapServers = cfg["Kafka:BootstrapServers"],
            GroupId = "backend-status-group",
            AutoOffsetReset = AutoOffsetReset.Earliest,
            EnableAutoCommit = false
        };

        _consumer = new ConsumerBuilder<Null, string>(config).Build();
        _consumer.Subscribe([KafkaTopics.JobCompleted, KafkaTopics.JobFailed]);
    }

    protected override Task ExecuteAsync(CancellationToken cancellationToken)
    {
        return Task.Run(() => ConsumeLoop(cancellationToken), cancellationToken);
    }

    private async Task ConsumeLoop(CancellationToken cancellationToken)
    {
        _logger.LogInformation("Kafka JobStatusConsumer запущен");

        while (!cancellationToken.IsCancellationRequested)
        {
            try
            {
                var result = _consumer.Consume(TimeSpan.FromSeconds(1));
                if (result?.Message?.Value is null)
                    continue;

                using var scope = _scopeFactory.CreateScope();
                var service = scope.ServiceProvider.GetRequiredService<IJobStatusService>();

                var evt = JsonSerializer.Deserialize<JobStatusEvent>(result.Message.Value) 
                    ?? throw new InvalidOperationException("Не валидное сообщение из Kafka");
                await service.HandleStatusAsync(result.Topic, evt, cancellationToken);

                _consumer.Commit(result);
            }
            catch (ConsumeException ex)
            {
                _logger.LogError(ex, "Ошибка! Kafka consume ошибка: {Error}", ex.Message);
            }
            catch (OperationCanceledException)
            {
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Ошибка! Неожиданная ошибка в consumer: {Error}", ex.Message);
                await Task.Delay(2000, cancellationToken);
            }
        }

        _consumer.Close();
    }

    public override void Dispose()
    {
        _consumer.Dispose();
        base.Dispose();
    }
}