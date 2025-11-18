using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace AudioProcessing.Domain.Entities.Track;

[Table("Tracks")]
public class TrackEntity
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

