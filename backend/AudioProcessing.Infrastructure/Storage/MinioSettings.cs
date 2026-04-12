namespace AudioProcessing.Infrastructure.Storage;

public class MinioSettings
{
    public string? Endpoint { get; set; }
    public string? AccessKey { get; set; }
    public string? SecretKey { get; set; }
    public bool Secure { get; set; } = true;
    public string? Bucket { get; set; }

    public override string ToString()
    {
        return $"MinioSettings [" +
               $"Endpoint={Endpoint ?? "null"}, " +
               $"AccessKey={AccessKey ?? "null"}, " +
               $"SecretKey={SecretKey}, " +
               $"Secure={Secure}, " +
               $"Bucket={Bucket ?? "null"}]";
    }
}
