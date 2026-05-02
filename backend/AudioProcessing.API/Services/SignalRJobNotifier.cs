using AudioProcessing.API.Services.Interfaces;
using AudioProcessing.Domain.Entities.Job;
using Microsoft.AspNetCore.SignalR;

namespace AudioProcessing.API.Services;

public class SignalRJobNotifier(IHubContext<JobHub> hub) : IJobNotifier
{
    public Task NotifyFinished(JobEntity job, CancellationToken ct)
    {
        return hub.Clients.Group(job.OutputKey!)
            .SendAsync("JobFinished", new
            {
                jobId = job.JobId,
                status = job.Status.ToString(),
                outputKey = job.OutputKey
            }, ct);
    }
}
