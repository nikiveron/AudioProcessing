// GetJobStatusModel.cs
namespace AudioProcessing.Application.Jobs.GetJobStatus;

public record GetJobStatusModel(
    Guid JobId, 
    string Status, 
    DateTime CreatedAt, 
    DateTime? StartedAt, 
    DateTime? FinishedAt, 
    string InputKey, 
    string OutputKey
);