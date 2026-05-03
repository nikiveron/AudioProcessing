using AudioProcessing.Domain.Exceptions;
using AudioProcessing.Domain.DTOs.Job;
using AudioProcessing.Domain.Entities.Job;
using AudioProcessing.Infrastructure.Database.Repositories;
using AudioProcessing.Worker.Services.Interfaces;

namespace AudioProcessing.Worker.Services;

public class JobPreparationService(
    JobsRepository jobsRepository,
    IKafkaPublisher publisher,
    ILogger<JobPreparationService> logger) : IJobPreparationService
{
    public async Task PrepareJobAsync(JobCreatedEvent evt, CancellationToken ct)
    {
        var job = await jobsRepository.Read(evt.JobId, ct);
        if (job == null)
        {
            logger.LogError("Ошибка! Job {JobId} не была найдена", evt.JobId);
            throw new HttpErrorException($"Задача по обработке не была найдена на сервере. Попробуйте еще раз.", System.Net.HttpStatusCode.NotFound);
        }

        job.Status = JobStatus.Running;
        await jobsRepository.Update(job, ct);

        var prepared = new JobPreparedEvent(
            evt.JobId,
            evt.InputKey,
            evt.OutputKey,
            new JobParameters(
            evt.Parameters.Genre,
            evt.Parameters.Instrument)
        );

        await publisher.ProducePrepared(prepared, ct);

        logger.LogInformation("Job {JobId} подготовлена и опубликована в Kafka", evt.JobId);
    }
}
