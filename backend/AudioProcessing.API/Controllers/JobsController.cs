using AudioProcessing.Infrastructure.Context;
using Microsoft.AspNetCore.Mvc;

namespace AudioProcessing.API.Controllers;

[ApiController]
[Route("api/jobs")]
public class JobsController(AppDbContext db) : ControllerBase
{
    private readonly AppDbContext _db = db;

    /// <summary>
    /// Метод возвращает статус задачи
    /// </summary>
    /// <param name="id"></param>
    /// <returns></returns>
    [HttpGet("{id:guid}")]
    public async Task<IActionResult> GetJobStatus([FromRoute] Guid id)
    {
        try
        {
            var job = await _db.Jobs.FindAsync(id);
            if (job == null)
                return NotFound(new { message = "Job not found" });

            return Ok(new
            {
                jobId = job.JobId,
                status = job.Status.ToString(),
                createdAt = job.CreatedAt,
                startedAt = job.StartedAt,
                finishedAt = job.FinishedAt,
                inputKey = job.InputKey,
                outputKey = job.OutputKey
            });
        }
        catch (Exception ex)
        {
            return StatusCode(500, ex.Message);
        }
    }
}