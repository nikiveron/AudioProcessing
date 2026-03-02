using AudioProcessing.Infrastructure.Context;
using AudioProcessing.Infrastructure.Storage;
using AudioProcessing.Domain.Entities.Track;
using AudioProcessing.Domain.Entities.Job;
using Confluent.Kafka;
using Microsoft.AspNetCore.Mvc;
using System.Text.Json;
using AudioProcessing.Domain.DTOs.Process;

namespace AudioProcessing.API.Controllers;

[ApiController]
[Route("api/process")]
public class ProcessController(IProducer<Null, string> producer, AppDbContext db, MinioService minio) : Controller
{
    private readonly IProducer<Null, string> _producer = producer;
    private readonly AppDbContext _db = db;
    private readonly string _outputTopic = "job.created";

    /// <summary>
    /// Принимает параметры (fileKey, genre, instrument), создаёт запись Job в БД и публикует сообщение в Kafka
    /// </summary>
    /// <param name="req"></param>
    /// <returns></returns>
    [HttpPost]
    public async Task<IActionResult> StartProcess([FromBody] ProcessRequestDto req)
    {
        TrackEntity track = await _db.Tracks.FindAsync(req.TrackId);
        if (track == null) return NotFound();

        var job = new JobEntity { JobId = Guid.NewGuid(), TrackId = track.TrackId, Status = JobStatus.Queued, InputKey = track.StorageKey, CreatedAt = DateTime.UtcNow };
        _db.Jobs.Add(job);
        await _db.SaveChangesAsync();

        var message = JsonSerializer.Serialize(new
        {
            jobId = job.JobId,
            inputKey = job.InputKey,
            outputKey = $"results/{job.JobId}_{track.Filename}",
            parameters = new { req.Genre, req.Instrument }
        });

        await _producer.ProduceAsync(_outputTopic, new Message<Null, string> { Value = message });
        _producer.Flush(TimeSpan.FromSeconds(5));

        return Ok(new { jobId = job.JobId });
    }
}

