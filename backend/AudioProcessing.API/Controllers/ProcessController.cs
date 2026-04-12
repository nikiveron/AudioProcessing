using AudioProcessing.Domain.DTOs.Process;
using AudioProcessing.Domain.Entities.Job;
using AudioProcessing.Domain.Entities.Track;
using AudioProcessing.Infrastructure.Repositories;
using Confluent.Kafka;
using Microsoft.AspNetCore.Mvc;
using System.Text.Json;

namespace AudioProcessing.API.Controllers;

[ApiController]
[Route("api/process")]
public class ProcessController(IProducer<Null, string> producer, JobsRepository jobsRepository, TracksRepository tracksRepository, ILogger<ProcessController> logger) : Controller
{
    private readonly IProducer<Null, string> _producer = producer;
    private readonly JobsRepository _jobsRepository = jobsRepository;
    private readonly TracksRepository _tracksRepository = tracksRepository;
    private readonly ILogger<ProcessController> _logger = logger;
    private readonly string _outputTopic = "job.created";

    /// <summary>
    /// Принимает параметры (fileKey, genre, instrument), создаёт запись Job в БД и публикует сообщение в Kafka
    /// </summary>
    /// <param name="req"></param>
    /// <returns></returns>
    [HttpPost]
    public async Task<IActionResult> StartProcess([FromBody] ProcessRequestDto req, CancellationToken ct)
    {
        _logger.LogInformation("ProcessController поступил POST запрос для TrackId {id}", req.TrackId);
        TrackEntity? track = await _tracksRepository.Read(req.TrackId, ct);
        if (track == null)
        {
            _logger.LogInformation("ProcessController ошибка 404 для TrackId {id}", req.TrackId);
            return NotFound();
        }

        var job = new JobEntity { JobId = Guid.NewGuid(), TrackId = track.TrackId, Status = JobStatus.Queued, InputKey = track.InputKey, OutputKey = track.OutputKey, CreatedAt = DateTime.UtcNow };
        await _jobsRepository.Create(job, ct);

        var message = JsonSerializer.Serialize(new
        {
            jobId = job.JobId,
            inputKey = job.InputKey,
            outputKey = job.OutputKey,
            parameters = new { genre = req.Genre, instrument = req.Instrument }
        });

        await _producer.ProduceAsync(_outputTopic, new Message<Null, string> { Value = message }, ct);
        _producer.Flush(TimeSpan.FromSeconds(5));

        _logger.LogInformation("ProcessController создано сообщение в топик {topic} для TrackId {id}", _outputTopic, req.TrackId);
        return Ok(new { jobId = job.JobId });
    }
}

