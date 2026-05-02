using AudioProcessing.Domain.Entities.Job;

namespace AudioProcessing.API.Services.Interfaces;

public interface IJobNotifier
{
    Task NotifyFinished(JobEntity job, CancellationToken ct);
}
