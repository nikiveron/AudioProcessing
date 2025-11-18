using AudioProcessing.Infrastructure.Context;
using AudioProcessing.Infrastructure.Storage;
using AudioProcessing.Domain.Entities.Process;
using AudioProcessing.Domain.Entities.Track;
using AudioProcessing.Domain.Entities.Job;
using Confluent.Kafka;
using Microsoft.AspNetCore.Mvc;
using System.Text.Json;

namespace AudioProcessing.API.Controllers;

[ApiController]
[Route("api/process")]
public class ProcessController(IProducer<Null, string> producer, AppDbContext db, MinioService minio) : Controller
{
    private readonly IProducer<Null, string> _producer = producer;
    private readonly AppDbContext _db = db;
    private readonly MinioService _minio = minio;

    [HttpPost]
    public async Task<IActionResult> StartProcess([FromBody] ProcessRequestEntity req)
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

        await _producer.ProduceAsync("audio-jobs", new Message<Null, string> { Value = message });
        _producer.Flush(TimeSpan.FromSeconds(5));

        return Ok(new { jobId = job.JobId });
    }
}

