namespace AudioProcessing.Domain.Enums;

public enum JobStatus
{
    Null = -1,
    Queued,
    Running,
    Success,
    Failed
}