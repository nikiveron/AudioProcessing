// UpdateJobModel.cs
namespace AudioProcessing.Application.Jobs.UpdateJob;

public record UpdateJobModel(Guid JobId, string Status, DateTime CreatedAt, DateTime? StartedAt, DateTime? FinishedAt, string InputKey, string OutputKey);