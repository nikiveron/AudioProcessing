using AudioProcessing.Domain.Entities.Job;
using AudioProcessing.Infrastructure.Repositories;
using Confluent.Kafka;
using System.Text.Json;
using Microsoft.AspNetCore.SignalR;

namespace AudioProcessing.API.Services;

public class JobStatusConsumer : BackgroundService
{
    private readonly ILogger<JobStatusConsumer> _logger;
    private readonly IServiceProvider _serviceProvider;
    private readonly IConsumer<Null, string> _consumer;
    private readonly IHubContext<JobHub> _hub;

    public JobStatusConsumer(
        ILogger<JobStatusConsumer> logger,
        IConfiguration cfg,
        IServiceProvider sp,
        IHubContext<JobHub> hub)
    {
        _logger = logger;
        _serviceProvider = sp;
        _hub = hub;

        var config = new ConsumerConfig
        {
            BootstrapServers = cfg["Kafka:BootstrapServers"],
            GroupId = "backend-status-group",
            AutoOffsetReset = AutoOffsetReset.Earliest,
            EnableAutoCommit = false
        };

        _consumer = new ConsumerBuilder<Null, string>(config).Build();
        _consumer.Subscribe(["job.completed", "job.failed"]);
    }

    protected override Task ExecuteAsync(CancellationToken stoppingToken)
    {
        return Task.Run(() => ConsumeLoop(stoppingToken), stoppingToken);
    }

    private async Task ConsumeLoop(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Kafka JobStatusConsumer started");

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                var cr = _consumer.Consume(TimeSpan.FromSeconds(1));
                if (cr == null || cr.Message?.Value == null)
                {
                    await Task.Delay(200, stoppingToken);
                    continue;
                }

                var payload = JsonSerializer.Deserialize<JsonElement>(cr.Message.Value);
                var jobId = Guid.Parse(payload.GetProperty("jobId").GetString());
                var outputKey = payload.TryGetProperty("outputKey", out var ok) ? ok.GetString() : null;
                var error = payload.TryGetProperty("error", out var err) ? err.GetString() : null;

                using var scope = _serviceProvider.CreateScope();
                var repo = scope.ServiceProvider.GetRequiredService<JobsRepository>();

                var job = await repo.Read(jobId, stoppingToken);
                if (job != null)
                {
                    job.Status = cr.Topic == "job.completed"
                        ? JobStatus.Success
                        : JobStatus.Failed;

                    job.OutputKey = outputKey ?? job.OutputKey;
                    job.ErrorDescription = error;
                    job.FinishedAt = DateTime.UtcNow;

                    await repo.Update(job, stoppingToken);

                    await _hub.Clients.Group(job.OutputKey)
                        .SendAsync("JobFinished", new
                        {
                            jobId = job.JobId,
                            status = job.Status.ToString(),
                            outputKey = job.OutputKey
                        }, stoppingToken);

                    _logger.LogInformation("Job {JobId} updated -> {Status}", jobId, job.Status);
                }

                _consumer.Commit(cr);
            }
            catch (ConsumeException ex)
            {
                _logger.LogError(ex, "Kafka consume error");
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Unexpected error in consumer");
                await Task.Delay(2000, stoppingToken);
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