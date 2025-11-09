using AudioProcessing.Infrastructure.Context;
using AudioProcessing.Infrastructure.Storage;
using Confluent.Kafka;
using System.Text.Json;

namespace AudioProcessing.Worker.Services;

public class JobConsumerService : BackgroundService
{
    private readonly IConsumer<Null, string> _consumer;
    private readonly IServiceProvider _serviceProvider; // для scope db/minio/http
    public JobConsumerService(IConfiguration cfg, IServiceProvider sp)
    {
        var conf = new ConsumerConfig
        {
            BootstrapServers = cfg["Kafka:BootstrapServers"],
            GroupId = "audio-workers-group",
            AutoOffsetReset = AutoOffsetReset.Earliest,
            EnableAutoCommit = false
        };
        _consumer = new ConsumerBuilder<Null, string>(conf).Build();
        _consumer.Subscribe("audio-jobs");
        _serviceProvider = sp;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                var cr = _consumer.Consume(stoppingToken);
                var payload = JsonSerializer.Deserialize<JsonElement>(cr.Message.Value);
                var jobId = Guid.Parse(payload.GetProperty("jobId").GetString());
                var inputKey = payload.GetProperty("inputKey").GetString();
                var outputKey = payload.GetProperty("outputKey").GetString();

                using var scope = _serviceProvider.CreateScope();
                var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
                var minio = scope.ServiceProvider.GetRequiredService<MinioService>();

                Job job = await db.Jobs.FindAsync(jobId);
                job.Status = JobStatus.Running; job.StartedAt = DateTime.UtcNow;
                await db.SaveChangesAsync(stoppingToken);

                // Download input
                using var inStream = await minio.GetObjectStreamAsync(inputKey);

                // Simulate processing (for prototype: copy stream or small transform)
                using var outStream = new MemoryStream();
                await inStream.CopyToAsync(outStream, stoppingToken);
                outStream.Position = 0;

                // Upload result
                await minio.UploadObjectAsync(outputKey, outStream, "audio/wav");

                job.OutputKey = outputKey;
                job.Status = JobStatus.Success;
                job.FinishedAt = DateTime.UtcNow;
                await db.SaveChangesAsync(stoppingToken);

                _consumer.Commit(cr);
            }
            catch (ConsumeException cx)
            {
                // логирование
            }
            catch (Exception ex)
            {
                // логирование
            }
        }
    }

    public override void Dispose()
    {
        _consumer.Close();
        _consumer.Dispose();
        base.Dispose();
    }
}

