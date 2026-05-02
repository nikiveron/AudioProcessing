
namespace AudioProcessing.Domain;

public static class KafkaTopics
{
    public const string JobCreated = "job.created";
    public const string JobPrepared = "job.prepared";
    public const string JobCompleted = "job.completed";
    public const string JobFailed = "job.failed";
}
