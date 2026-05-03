using AudioProcessing.Domain.Exceptions;
using AudioProcessing.Infrastructure.Storage;
using MediatR;
using Microsoft.Extensions.Logging;
using System.Net;

namespace AudioProcessing.Application.Files.DownloadFile;

public record DownloadFileQuery(string ObjectKey) : IRequest<DownloadFileModel>;

public class DownloadFileHandler(
    ILogger<DownloadFileHandler> logger,
    MinioService minio
) : IRequestHandler<DownloadFileQuery, DownloadFileModel>
{
    public async Task<DownloadFileModel> Handle(DownloadFileQuery request, CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(request.ObjectKey))
            throw new HttpErrorException("Ошибка! ObjectKey обязательный параметр", HttpStatusCode.BadRequest);

        try
        {
            var stream = await minio.GetObjectStreamAsync(request.ObjectKey, cancellationToken);
            var fileName = Path.GetFileName(request.ObjectKey);
            var ext = Path.GetExtension(fileName).ToLowerInvariant();

            var contentType = ext switch
            {
                ".wav" => "audio/wav",
                ".mp3" => "audio/mpeg",
                ".ogg" => "audio/ogg",
                _ => "application/octet-stream"
            };

            logger.LogInformation("Скачивание файла {objectKey} из MinIO", request.ObjectKey);

            return new DownloadFileModel(stream, contentType, fileName);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Ошибка скачивания файла {objectKey}", request.ObjectKey);
            throw new HttpErrorException("Ошибка! Файл не был найден.", HttpStatusCode.NotFound);
        }
    }
}
