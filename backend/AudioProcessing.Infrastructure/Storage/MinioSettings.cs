namespace AudioProcessing.Infrastructure.Storage;

public class MinioSettings
{
    public string? Endpoint { get; set; }
    public string? AccessKey { get; set; }
    public string? SecretKey { get; set; }
    public bool Secure { get; set; } = true;
    public string? Bucket { get; set; }
}
