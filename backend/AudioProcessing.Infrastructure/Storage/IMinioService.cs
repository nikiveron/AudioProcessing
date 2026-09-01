
namespace AudioProcessing.Infrastructure.Storage;

public interface IMinioService
{
    public Task EnsureBucketExistsAsync(CancellationToken ct);
    public Task UploadObjectAsync(string objectName, Stream data, string contentType, CancellationToken ct);
    public Task<Stream> GetObjectStreamAsync(string objectName, CancellationToken cancellationToken);
    public Task<bool> ObjectExistsAsync(string objectName, CancellationToken ct);
}
