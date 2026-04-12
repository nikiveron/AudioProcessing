namespace AudioProcessing.Domain.DTOs.TracksController;

public class CreateTrackRequest
{
    public string Filename { get; set; } = string.Empty;
    public string InputKey { get; set; } = string.Empty;
    public string OutputKey { get; set; } = string.Empty;
}