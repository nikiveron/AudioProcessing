
namespace AudioProcessing.Domain.DTOs.Job;

public record JobPreparedEvent(
    Guid JobId,
    string InputKey,
    string OutputKey,
    MusicGenre Genre,
    MusicInstrument Instrument
);
