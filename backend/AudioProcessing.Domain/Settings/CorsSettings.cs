namespace AudioProcessing.Domain.Settings;

public class CorsSettings
{
    public const string Section = "Cors";
    public string[] AllowedOrigins { get; init; } = [];
}
