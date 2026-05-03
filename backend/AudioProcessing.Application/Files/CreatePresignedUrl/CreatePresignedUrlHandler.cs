using MediatR;
using Microsoft.Extensions.Logging;
using AudioProcessing.Infrastructure.Storage;
using System.Net;
using AudioProcessing.Domain.Exceptions;

namespace AudioProcessing.Application.Files.CreatePresignedUrl;

public record CreatePresignedUrlCommand(
    string Filename, 
    string InputPath, 
    string OutputPath
) : IRequest<CreatePresignedUrlModel>;

public class CreatePresignedUrlHandler(
    ILogger<CreatePresignedUrlHandler> logger, 
    MinioService minio
) : IRequestHandler<CreatePresignedUrlCommand, CreatePresignedUrlModel>
{
    public async Task<CreatePresignedUrlModel> Handle(CreatePresignedUrlCommand request, CancellationToken cancellationToken)
    {
        logger.LogInformation("FilesController поступил POST запрос для файла {request}", request.Filename);
        if (string.IsNullOrEmpty(request.Filename))
        {
            logger.LogInformation("FilesController ошибка 400 для файла {request}", request.Filename);
            throw new HttpErrorException("Ошибка! Имя файла обязательный параметр", HttpStatusCode.BadRequest);
        }

        try
        {
            var trackGuid = Guid.NewGuid();
            string inputKey = $"{request.InputPath}/{trackGuid}_{request.Filename}";
            string outputKey = $"{request.OutputPath}/{trackGuid}_{request.Filename}";
            string url = minio.PresignedPutObject(inputKey, 3600);

            logger.LogInformation("FilesController место для файла {request} выделено", request.Filename);
            return new CreatePresignedUrlModel(url, inputKey, outputKey);
        }
        catch (Exception ex)
        {
            logger.LogError("FilesController ошибка 500 для файла {request}", request.Filename);
            throw new HttpErrorException($"Ошибка! {ex.Message}", HttpStatusCode.InternalServerError);
        }
    }
}
