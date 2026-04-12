using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace AudioProcessing.Domain.Entities.Track;

[Table("Tracks")]
public class TrackEntity
{
    [Key]
    [Column("track_id")]
    public Guid TrackId { get; set; }

    [Column("input_key")]
    public string InputKey { get; set; } = string.Empty;

    [Column("output_key")]
    public string OutputKey { get; set; } = string.Empty;

    [Column("filename")]
    public string Filename { get; set; } = string.Empty;

    [Column("created_at")]
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [Column("deleted_at")]
    public DateTime? DeletedAt { get; set; }
}

