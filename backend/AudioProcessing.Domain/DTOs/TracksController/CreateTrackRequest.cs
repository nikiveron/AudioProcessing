namespace AudioProcessing.Domain.DTOs.TracksController;

public class CreateTrackRequest
{
    public string Filename { get; set; } = null!;
    public string StorageKey { get; set; } = null!;
}