namespace AudioProcessing.Domain.Requests.Process;

public class ProcessRequestDto
{
    public Guid TrackId { get; set; }
    public string? Instrument { get; set; }
}