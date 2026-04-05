using Microsoft.Extensions.Options;
using Minio;
using Minio.DataModel.Args;

namespace AudioProcessing.Infrastructure.Storage;

public class MinioService
{
    private readonly IMinioClient _client;
    private readonly string _bucket;

    public MinioService(IMinioClient client, IOptions<MinioSettings> settings)
    {
        _client = client ?? throw new ArgumentNullException(nameof(client));
        var s = settings?.Value ?? throw new ArgumentNullException(nameof(settings));
        _bucket = string.IsNullOrWhiteSpace(s.Bucket) ? "audio" : s.Bucket;
    }

    public async Task EnsureBucketExistsAsync(CancellationToken ct)
    {
        try
        {
            bool exists = await _client.BucketExistsAsync(new BucketExistsArgs().WithBucket(_bucket), ct);
            if (!exists)
                await _client.MakeBucketAsync(new MakeBucketArgs().WithBucket(_bucket), ct);
        }
        catch (Exception ex)
        {
            // логируем, но не пробрасываем дальше — инициализация может быть отложена
            Console.WriteLine($"Minio EnsureBucketExistsAsync failed: {ex.Message}");
            throw;
        }
    }

    public async Task UploadObjectAsync(string objectName, Stream data, string contentType, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(data);

        await _client.PutObjectAsync(new PutObjectArgs()
            .WithBucket(_bucket)
            .WithObject(objectName)
            .WithStreamData(data)
            .WithObjectSize(data.Length)
            .WithContentType(contentType), 
            ct);
    }

    public async Task<Stream> GetObjectStreamAsync(string objectName, CancellationToken cancellationToken)
    {
        var ms = new MemoryStream();
        await _client.GetObjectAsync(new GetObjectArgs().WithBucket(_bucket).WithObject(objectName)
            .WithCallbackStream((stream) => stream.CopyTo(ms)), cancellationToken);
        ms.Position = 0;
        return ms;
    }

    public string PresignedGetObject(string objectName, int expirySeconds = 3600)
    {
        var args = new PresignedGetObjectArgs()
            .WithBucket(_bucket)
            .WithObject(objectName)
            .WithExpiry(expirySeconds);

        return _client.PresignedGetObjectAsync(args).GetAwaiter().GetResult();
    }

    public string PresignedPutObject(string objectName, int expirySeconds = 3600)
    {
        var args = new PresignedPutObjectArgs()
            .WithBucket(_bucket)
            .WithObject(objectName)
            .WithExpiry(expirySeconds);

        return _client.PresignedPutObjectAsync(args).GetAwaiter().GetResult();
    }

    public async Task<bool> ObjectExistsAsync(string objectName, CancellationToken ct)
    {
        try
        {
            await _client.StatObjectAsync(new StatObjectArgs().WithBucket(_bucket).WithObject(objectName), ct);
            return true;
        }
        catch
        {
            return false;
        }
    }
}
