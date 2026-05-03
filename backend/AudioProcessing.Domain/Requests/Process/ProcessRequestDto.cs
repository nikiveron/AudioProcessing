
namespace AudioProcessing.Domain.DTOs.Process;

public class ProcessRequestDto
{
    public Guid TrackId { get; set; }
    public MusicInstrument Instrument { get; set; }
}