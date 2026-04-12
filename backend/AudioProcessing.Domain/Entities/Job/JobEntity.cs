using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace AudioProcessing.Domain.Entities.Job;

[Table("Jobs")]
public class JobEntity
{
    [Key]
    [Column("job_id")]
    public Guid JobId { get; set; }

    [Column("track_id")]
    public Guid TrackId { get; set; }

    [Column("track_status")]
    public JobStatus Status { get; set; }

    [Column("input_key")]
    public string InputKey { get; set; } = string.Empty;

    [Column("output_key")]
    public string OutputKey { get; set; } = string.Empty;

    [Column("created_at")]
    public DateTime CreatedAt { get; set; }

    [Column("started_at")]
    public DateTime? StartedAt { get; set; }

    [Column("finished_at")]
    public DateTime? FinishedAt { get; set; }

    [Column("error_description")]
    public string? ErrorDescription { get; set; }
}

public enum JobStatus
{
    Null = -1,
    Queued,
    Running,
    Success,
    Failed
}