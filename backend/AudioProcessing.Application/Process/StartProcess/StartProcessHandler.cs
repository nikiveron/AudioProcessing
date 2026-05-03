using AudioProcessing.Domain.Exceptions;
using AudioProcessing.Domain.Entities.Job;
using AudioProcessing.Domain.Entities.Track;
using AudioProcessing.Infrastructure.Database.Repositories;
using Confluent.Kafka;
using MediatR;
using Microsoft.Extensions.Logging;
using System.Net;
using System.Text.Json;

namespace AudioProcessing.Application.Process.StartProcess;

public record StartProcessCommand(Guid TrackId, string Instrument, string OutputTopic) : IRequest<Guid>;

public class StartProcessHandler(
    ILogger<StartProcessHandler> logger,
    TracksRepository tracksRepository,
    JobsRepository jobsRepository,
    IProducer<Null, string> producer
) : IRequestHandler<StartProcessCommand, Guid>
{
    public async Task<Guid> Handle(StartProcessCommand request, CancellationToken cancellationToken)
    {
        logger.LogInformation("ProcessController поступил POST запрос для TrackId {id}", request.TrackId);
        TrackEntity? track = await tracksRepository.Read(request.TrackId, cancellationToken);
        if (track == null)
        {
            logger.LogInformation("ProcessController ошибка 404 для TrackId {id}", request.TrackId);
            throw new HttpErrorException($"Ошибка! TrackId {request.TrackId} не был найден", HttpStatusCode.NotFound);
        }

        var job = new JobEntity { JobId = Guid.NewGuid(), TrackId = track.TrackId, Status = JobStatus.Queued, InputKey = track.InputKey, OutputKey = track.OutputKey, CreatedAt = DateTime.UtcNow };
        await jobsRepository.Create(job, cancellationToken);

        var message = JsonSerializer.Serialize(new
        {
            job.JobId,
            job.InputKey,
            job.OutputKey,
            Parameters = new { request.Instrument }
        });

        await producer.ProduceAsync(request.OutputTopic, new Message<Null, string> { Value = message }, cancellationToken);
        producer.Flush(TimeSpan.FromSeconds(5));

        logger.LogInformation("ProcessController создано сообщение в топик {topic} для TrackId {trackId} с JobId {jobId}", request.OutputTopic, request.TrackId, job.JobId);
        return job.JobId;
    }
}
