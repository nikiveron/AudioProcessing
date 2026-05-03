namespace AudioProcessing.Domain.DTOs.Job;

public record JobCreatedEvent(
Guid JobId,
string InputKey,
string OutputKey,
JobParameters Parameters
);
