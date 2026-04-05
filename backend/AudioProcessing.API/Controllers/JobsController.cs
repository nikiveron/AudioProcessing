using AudioProcessing.Infrastructure.Repositories;
using AudioProcessing.Domain.DTOs.JobsController;
using Microsoft.AspNetCore.Mvc;
using AudioProcessing.Domain.Entities.Job;

namespace AudioProcessing.API.Controllers;

[ApiController]
[Route("api/jobs")]
public class JobsController(JobsRepository jobsRepository, ILogger<JobsController> logger) : ControllerBase
{
    private readonly JobsRepository _jobsRepository = jobsRepository;
    private readonly ILogger<JobsController> _logger = logger;

    /// <summary>
    /// Метод возвращает статус задачи
    /// </summary>
    /// <param name="id"></param>
    /// <returns></returns>
    [HttpGet("{id:guid}")]
    public async Task<IActionResult> GetJobStatus([FromRoute] Guid id, CancellationToken ct)
    {
        _logger.LogInformation("JobsController поступил GET запрос для job с id {id}", id);
        try
        {
            var job = await _jobsRepository.Read(id, ct);
            if (job == null)
            {
                _logger.LogInformation("JobsController ошибка 404 для job с id {id}", id);
                return NotFound(new { message = "Job not found" });
            }

            _logger.LogInformation("JobsController найден статус для job с id {id}", id);
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
            _logger.LogInformation("JobsController ошибка 500 для job с id {id}", id);
            return StatusCode(500, ex.Message);
        }
    }

    [HttpPut("{id:guid}")]
    public async Task<IActionResult> UpdateJob(Guid id, UpdateJobRequest req, CancellationToken ct)
    {
        _logger.LogInformation("JobsController поступил PUT запрос для job с id {id}", id);
        try
        {
            var job = await _jobsRepository.Read(id, ct);
            if (job == null)
            {
                _logger.LogInformation("JobsController ошибка 404 для job с id {id}", id);
                return NotFound(new { message = "Job not found" });
            }

            job.Status = req.Status != JobStatus.Null ? req.Status : job.Status;
            job.OutputKey = string.IsNullOrEmpty(req.OutputKey) ? job.OutputKey : req.OutputKey;
            job.StartedAt = req.StartedAt == null ? job.StartedAt : req.StartedAt;
            job.FinishedAt = req.FinishedAt == null ? job.FinishedAt : req.FinishedAt;

            await _jobsRepository.Update(job, ct);

            _logger.LogInformation("JobsController обновлены значения для job с id {id}", id);
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
            _logger.LogInformation("JobsController ошибка 500 для id {id}", id);
            return StatusCode(500, ex.Message);
        }
    }
}