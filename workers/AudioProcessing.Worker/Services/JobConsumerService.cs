using AudioProcessing.Domain.Entities.Job;
using AudioProcessing.Infrastructure.Context;
using AudioProcessing.Infrastructure.Storage;
using Confluent.Kafka;
using System.Text.Json;

namespace AudioProcessing.Worker.Services;

public class JobConsumerService : BackgroundService
{
    private readonly IConsumer<Null, string> _consumer;
    private readonly IServiceProvider _serviceProvider; // для scope db/minio/http
    private readonly string _topicName = "audio-jobs";

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
        _consumer.Subscribe(_topicName);
        _serviceProvider = sp;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                // получаем сообщение
                var cr = _consumer.Consume(stoppingToken);

                // десереализация сообщения
                var payload = JsonSerializer.Deserialize<JsonElement>(cr.Message.Value);
                var jobId = Guid.Parse(payload.GetProperty("jobId").GetString());
                var inputKey = payload.GetProperty("inputKey").GetString();
                var outputKey = payload.GetProperty("outputKey").GetString();

                // новый DI-scope на каждую задачу для
                // DbContext корректно создавался и уничтожался
                // не было утечек соединений с БД
                using var scope = _serviceProvider.CreateScope();

                // получение сервисов
                var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
                var minio = scope.ServiceProvider.GetRequiredService<MinioService>();

                // обновление статуса задания
                JobEntity job = await db.Jobs.FindAsync(jobId, stoppingToken);
                job.Status = JobStatus.Running; 
                job.StartedAt = DateTime.UtcNow;
                await db.SaveChangesAsync(stoppingToken);

                // Загрузка входного файла из MinIO в виде потока, без сохранения на диск.
                using var inStream = await minio.GetObjectStreamAsync(inputKey);

                // Имитация обработки
                using var outStream = new MemoryStream();
                await inStream.CopyToAsync(outStream, stoppingToken); // файл просто копируется
                outStream.Position = 0;

                // Загрузка результата
                await minio.UploadObjectAsync(outputKey, outStream, "audio/wav");

                // Финализация задания
                job.OutputKey = outputKey;
                job.Status = JobStatus.Success;
                job.FinishedAt = DateTime.UtcNow;
                await db.SaveChangesAsync(stoppingToken);

                // Подтверждение сообщения Kafka. Offset коммитится только после успешной обработки.
                _consumer.Commit(cr);
            }
            catch (ConsumeException ex)
            {
                // логирование
            }
            catch (Exception ex)
            {
                // логирование
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

