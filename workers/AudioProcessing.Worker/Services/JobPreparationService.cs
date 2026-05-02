using AudioProcessing.Domain;
using AudioProcessing.Domain.DTOs.Job;
using AudioProcessing.Domain.Entities.Job;
using AudioProcessing.Infrastructure.Database.Repositories;
using AudioProcessing.Worker.Services.Interfaces;

namespace AudioProcessing.Worker.Services;

public class JobPreparationService : IJobPreparationService
{
    private readonly JobsRepository _jobsRepository;
    private readonly IKafkaPublisher _publisher;
    private readonly ILogger<JobPreparationService> _logger;

    public JobPreparationService(
        JobsRepository jobsRepository,
        IKafkaPublisher publisher,
        ILogger<JobPreparationService> logger)
    {
        _jobsRepository = jobsRepository;
        _publisher = publisher;
        _logger = logger;
    }

    public async Task PrepareJobAsync(JobCreatedEvent evt, CancellationToken ct)
    {
        var job = await _jobsRepository.Read(evt.JobId, ct);
        if (job == null)
        {
            _logger.LogError("Job {JobId} not found", evt.JobId);
            return;
        }

        job.Status = JobStatus.Running;
        await _jobsRepository.Update(job, ct);

        var prepared = new JobPreparedEvent(
            evt.JobId,
            evt.InputKey,
            evt.OutputKey,
            Enum.Parse<MusicGenre>(evt.Parameters.Genre),
            Enum.Parse<MusicInstrument>(evt.Parameters.Instrument)
        );

        await _publisher.ProducePrepared(prepared, ct);

        _logger.LogInformation("Job {JobId} prepared and published", evt.JobId);
    }
}
