using AudioProcessing.API.Services.Interfaces;
using AudioProcessing.Domain;
using AudioProcessing.Domain.DTOs.Job;
using AudioProcessing.Domain.Entities.Job;
using AudioProcessing.Infrastructure.Database.Repositories;

namespace AudioProcessing.API.Services;

public class JobStatusService(
    JobsRepository repo,
    IJobNotifier notifier,
    ILogger<JobStatusService> logger) : IJobStatusService
{
    public async Task HandleStatusAsync(string topic, JobStatusEvent evt, CancellationToken ct)
    {
        var job = await repo.Read(evt.JobId, ct);
        if (job == null) return;

        job.Status = topic == KafkaTopics.JobCompleted ? JobStatus.Success : JobStatus.Failed;
        job.OutputKey = evt.OutputKey ?? job.OutputKey;
        job.ErrorDescription = evt.Error;
        job.FinishedAt = DateTime.UtcNow;

        await repo.Update(job, ct);
        await notifier.NotifyFinished(job, ct);

        logger.LogInformation("Job {JobId} обновлен статус -> {Status}", job.JobId, job.Status);
    }
}