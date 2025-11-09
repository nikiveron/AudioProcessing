using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace AudioProcessing.Domain.Entities.Process;

public class ProcessRequest
{
    [Key]
    [Column("process_request_id")]
    public Guid ProcessRequestId { get; set; }

    [Column("track_id")]
    public Guid TrackId { get; set; }

    [Column("genre")]
    public MusicGenre Genre { get; set; }

    [Column("instrument")]
    public MusicInstrument Instrument { get; set; }

    [Column("created_at")]
    public DateTime CreatedAt { get; set; }

    [Column("deleted_at")]
    public DateTime? DeletedAt { get; set; }
}

public enum MusicGenre
{
    Classic,
    Jazz,
    Rock
}

public enum MusicInstrument
{
    Guitar,
    Piano,
    Vocal
}