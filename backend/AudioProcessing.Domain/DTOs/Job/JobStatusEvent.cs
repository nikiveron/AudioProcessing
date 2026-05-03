namespace AudioProcessing.Domain.DTOs.Job;

public record JobStatusEvent(
    Guid JobId,
    string? OutputKey,
    string? Error
);
