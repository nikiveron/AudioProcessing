using AudioProcessing.Domain.DTOs.Job;

namespace AudioProcessing.Worker.Services.Interfaces;

public interface IJobPreparationService
{
    Task PrepareJobAsync(JobCreatedEvent evt, CancellationToken ct);
}
