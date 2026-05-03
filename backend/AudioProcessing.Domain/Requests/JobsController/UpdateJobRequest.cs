using AudioProcessing.Domain.Entities.Job;

namespace AudioProcessing.Domain.DTOs.JobsController;

public class UpdateJobRequest
{
    public JobStatus Status { get; set; }
    public string OutputKey { get; set; } = string.Empty;
    public DateTime? StartedAt { get; set; }
    public DateTime? FinishedAt { get; set; }
}
