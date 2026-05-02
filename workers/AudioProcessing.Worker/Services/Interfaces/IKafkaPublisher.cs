using AudioProcessing.Domain.DTOs.Job;

namespace AudioProcessing.Worker.Services.Interfaces;

public interface IKafkaPublisher
{
    Task ProducePrepared(JobPreparedEvent evt, CancellationToken ct);
}
