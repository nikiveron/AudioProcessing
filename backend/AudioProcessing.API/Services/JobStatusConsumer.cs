using AudioProcessing.API.Services.Interfaces;
using AudioProcessing.Domain;
using AudioProcessing.Domain.DTOs.Job;
using AudioProcessing.Domain.Exceptions;
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
            JobStatusEvent? currentJob = null;
            try
            {
                var result = _consumer.Consume(TimeSpan.FromSeconds(1));
                if (result?.Message?.Value is null)
                    continue;

                using var scope = _scopeFactory.CreateScope();
                var service = scope.ServiceProvider.GetRequiredService<IJobStatusService>();

                var evt = JsonSerializer.Deserialize<JobStatusEvent>(result.Message.Value) 
                    ?? throw new InvalidOperationException("Не валидное сообщение из Kafka");

                currentJob = evt;

                await service.HandleStatusAsync(result.Topic, evt, cancellationToken);

                _consumer.Commit(result);
            }
            catch (ConsumeException ex)
            {
                _logger.LogError("Ошибка! Kafka consume ошибка: {Error}", ex.Message);
                await NotifyFailureEvent(currentJob, ex.Message, cancellationToken);
            }
            catch (OperationCanceledException ex)
            {
                _logger.LogWarning("Внимание! Операция была отменена: {Error}", ex.Message);
                await NotifyFailureEvent(currentJob, ex.Message, cancellationToken);
            }
            catch (HttpErrorException ex)
            {
                _logger.LogError("Ошибка! {Error}", ex.ErrorMessage);
                await NotifyFailureEvent(currentJob, ex.ErrorMessage, cancellationToken);
            }
            catch (Exception ex)
            {
                _logger.LogError("Ошибка! Неожиданная ошибка в consumer: {Error}", ex.Message);
                await NotifyFailureEvent(currentJob, ex.Message, cancellationToken);
            }
        }
    }

    private async Task NotifyFailureEvent(JobStatusEvent? job, string errorMessage, CancellationToken cancellationToken)
    {
        try
        {
            using var scope = _scopeFactory.CreateScope();
            var notifier = scope.ServiceProvider.GetRequiredService<IJobNotifier>();

            var failureEvent = new JobStatusEvent(
                JobId: job == null ? Guid.Empty : job.JobId,
                OutputKey: job == null ? string.Empty : job.OutputKey,
                Error: errorMessage
            );

            await notifier.NotifyFailed(failureEvent, cancellationToken);
            _logger.LogInformation("Failure event отправлен по SignalR");
        }
        catch (Exception pubEx)
        {
            _logger.LogError(pubEx, "Ошибка отправлния failure event по SignalR");
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