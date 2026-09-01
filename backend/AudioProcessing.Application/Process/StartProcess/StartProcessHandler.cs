// StartProcessHandler.cs
using AudioProcessing.Domain;
using AudioProcessing.Domain.Entities.Job;
using AudioProcessing.Domain.Entities.Track;
using AudioProcessing.Domain.Enums;
using AudioProcessing.Domain.Exceptions;
using AudioProcessing.Infrastructure.Database.Repositories.Interfaces;
using Confluent.Kafka;
using MediatR;
using Microsoft.Extensions.Logging;
using System.Net;
using System.Text.Json;

namespace AudioProcessing.Application.Process.StartProcess;

public record StartProcessCommand(Guid TrackId, string? Instrument) : IRequest<Guid>;

public class StartProcessHandler(
    ILogger<StartProcessHandler> logger,
    ITracksRepository tracksRepository,
    IJobsRepository jobsRepository,
    IProducer<Null, string> producer
) : IRequestHandler<StartProcessCommand, Guid>
{
    public async Task<Guid> Handle(StartProcessCommand request, CancellationToken cancellationToken)
    {
        var instrument = request.Instrument;
        var allowedTypes = Enum.GetNames<MusicInstrument>();
        if (string.IsNullOrEmpty(instrument) || !allowedTypes.Contains(instrument))
            throw new HttpErrorException(ExceptionDictionary.UnavaliableInstrument, HttpStatusCode.BadRequest);

        logger.LogInformation("ProcessController поступил POST запрос для TrackId {id}", request.TrackId);
        TrackEntity? track = await tracksRepository.Read(request.TrackId, cancellationToken);
        if (track == null)
        {
            logger.LogInformation("ProcessController ошибка 404 для TrackId {id}", request.TrackId);
            throw new HttpErrorException(ExceptionDictionary.TrackNotFound, HttpStatusCode.NotFound);
        }

        var job = new JobEntity { JobId = Guid.NewGuid(), TrackId = track.TrackId, Status = JobStatus.Queued, InputKey = track.InputKey, OutputKey = track.OutputKey, CreatedAt = DateTime.UtcNow };

        try
        {
            await jobsRepository.Create(job, cancellationToken);
        }
        catch (ArgumentNullException)
        {
            throw new HttpErrorException(ExceptionDictionary.NullJobCreationFailed, HttpStatusCode.BadRequest);
        }
        catch
        {
            throw new HttpErrorException(ExceptionDictionary.JobCreationFailed, HttpStatusCode.InternalServerError);
        }

        var message = JsonSerializer.Serialize(new
        {
            job.JobId,
            job.InputKey,
            job.OutputKey,
            Parameters = new { request.Instrument }
        });

        try
        {
            await producer.ProduceAsync(KafkaTopics.JobCreated, new Message<Null, string> { Value = message }, cancellationToken);
            producer.Flush(TimeSpan.FromSeconds(5));
        }
        catch (ProduceException<Null, string> ex)
        {
            logger.LogError(ex, "Ошибка публикации сообщения в Kafka. Topic: {Topic}, Error: {Error}", "job.completed", ex.Error.Reason);
            throw new HttpErrorException(ExceptionDictionary.KafkaProducerError, HttpStatusCode.InternalServerError);
        }
        catch (KafkaException ex)
        {
            logger.LogError(ex, "Ошибка Kafka: {Error}", ex.Error.Reason);
            throw new HttpErrorException(ExceptionDictionary.KafkaProducerError, HttpStatusCode.InternalServerError);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Необработанная ошибка при отправке сообщения");
            throw new HttpErrorException(ExceptionDictionary.KafkaProducerError, HttpStatusCode.InternalServerError);
        }

        logger.LogInformation("ProcessController создано сообщение в топик {topic} для TrackId {trackId} с JobId {jobId}", KafkaTopics.JobCreated, request.TrackId, job.JobId);
        return job.JobId;
    }
}
