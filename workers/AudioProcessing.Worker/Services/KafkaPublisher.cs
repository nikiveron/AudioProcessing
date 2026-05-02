using AudioProcessing.Domain;
using AudioProcessing.Domain.DTOs.Job;
using AudioProcessing.Worker.Services.Interfaces;
using Confluent.Kafka;
using System.Text.Json;

namespace AudioProcessing.Worker.Services;

public class KafkaPublisher : IKafkaPublisher
{
    private readonly IProducer<Null, string> _producer;

    public KafkaPublisher(IConfiguration cfg)
    {
        var config = new ProducerConfig
        {
            BootstrapServers = cfg["Kafka:BootstrapServers"],
            EnableIdempotence = true,
            Acks = Acks.All
        };

        _producer = new ProducerBuilder<Null, string>(config).Build();
    }

    public Task ProducePrepared(JobPreparedEvent evt, CancellationToken ct)
    {
        var json = JsonSerializer.Serialize(evt);
        return _producer.ProduceAsync(
            KafkaTopics.JobPrepared,
            new Message<Null, string> { Value = json },
            ct);
    }
}