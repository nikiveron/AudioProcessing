using Microsoft.EntityFrameworkCore;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace AudioProcessing.Infrastructure.Context;
public class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options)
{
    public DbSet<Track> Tracks { get; set; }
    public DbSet<Job> Jobs { get; set; }
}

public class Track
{
    [Key]
    [Column("track_id")]
    public Guid TrackId { get; set; }

    [Column("storage_key")]
    public string StorageKey { get; set; } = string.Empty;

    [Column("filename")]
    public string Filename { get; set; } = string.Empty;

    [Column("deleted_at")]
    public DateTime? DeletedAt { get; set; }
}

public class Job
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
}

public enum JobStatus
{
    Queued,
    Running,
    Success,
    Error
}