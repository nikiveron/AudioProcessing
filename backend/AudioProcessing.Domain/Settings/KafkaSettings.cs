namespace AudioProcessing.Domain.Settings;

public class KafkaSettings
{
    public const string Section = "Kafka";
    public string BootstrapServers { get; init; } = string.Empty;
}
