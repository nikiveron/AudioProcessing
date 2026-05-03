using AudioProcessing.Domain.Exceptions;
using AudioProcessing.Infrastructure.Storage;
using MediatR;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;
using System.Net;

namespace AudioProcessing.Application.Files.UploadFile;

public record UploadFileCommand(IFormFile File) : IRequest<UploadFileModel>;

public class UploadFileHandler(
    ILogger<UploadFileHandler> logger,
    MinioService minio
) : IRequestHandler<UploadFileCommand, UploadFileModel>
{
    public async Task<UploadFileModel> Handle(UploadFileCommand request, CancellationToken cancellationToken)
    {
        if (request.File == null || request.File.Length == 0)
            throw new HttpErrorException("Ошибка! Файл не был загружен", HttpStatusCode.BadRequest);

        var trackGuid = Guid.NewGuid();
        string inputKey = $"input/{trackGuid}_{request.File.FileName}";
        string outputKey = $"output/{trackGuid}_{request.File.FileName}";

        try
        {
            using var stream = request.File.OpenReadStream();
            await minio.UploadObjectAsync(inputKey, stream, request.File.ContentType, cancellationToken);

            logger.LogInformation("Файл {Filename} загружен в MinIO его key:{Key}", request.File.FileName, inputKey);

            return new (inputKey, outputKey);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Ошибка загрузки файла {Filename} в хранилище", request.File.FileName);
            throw new HttpErrorException("Ошибка при загрузке файла в хранилище", HttpStatusCode.InternalServerError);
        }
    }
}