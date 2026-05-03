using AudioProcessing.Domain.DTOs.Job;

namespace AudioProcessing.API.Services.Interfaces;

public interface IJobStatusService
{
    Task HandleStatusAsync(string topic, JobStatusEvent evt, CancellationToken ct);
}
