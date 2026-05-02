using AudioProcessing.Domain;
using AudioProcessing.Domain.Entities.Track;
using AudioProcessing.Infrastructure.Database.Repositories;
using AudioProcessing.Infrastructure.Storage;
using MediatR;
using Microsoft.Extensions.Logging;
using System.Net;

namespace AudioProcessing.Application.Tracks.CreateTrack;

public record CreateTrackCommand(
    string Filename,
    string InputKey,
    string OutputKey
) : IRequest<CreateTrackModel>;

public class CreateTrackHandler(
    ILogger<CreateTrackHandler> logger,
    TracksRepository tracksRepository,
    MinioService minio
) : IRequestHandler<CreateTrackCommand, CreateTrackModel>
{
    public async Task<CreateTrackModel> Handle(CreateTrackCommand request, CancellationToken cancellationToken)
    {
        logger.LogInformation("TracksController поступил POST запрос для Filename {filename}", request.Filename);
        // проверяем полученные данные
        if (string.IsNullOrWhiteSpace(request.Filename) || string.IsNullOrWhiteSpace(request.InputKey) || string.IsNullOrWhiteSpace(request.OutputKey))
        {
            string exception = "Filename, OutputKey и InputKey обязательные параметры";
            logger.LogInformation("TracksController ошибка 400 для Filename {filename}: {exception}", request.Filename, exception);
            throw new HttpErrorException($"Ошибка! {exception}", HttpStatusCode.BadRequest);
        }

        // проверяем существует ли файл в minio
        bool exists = await minio.ObjectExistsAsync(request.InputKey, cancellationToken);
        if (!exists)
        {
            string exception = "Файл не был найден в хранилище Minio";
            logger.LogInformation("TracksController ошибка 404 для Filename {filename}: {exception}", request.Filename, exception);
            throw new HttpErrorException($"Ошибка! {exception}", HttpStatusCode.NotFound);
        }

        var track = new TrackEntity
        {
            TrackId = Guid.NewGuid(),
            Filename = request.Filename,
            InputKey = request.InputKey,
            OutputKey = request.OutputKey,
            CreatedAt = DateTime.UtcNow
        };

        await tracksRepository.Create(track, cancellationToken);

        logger.LogInformation("TracksController трек Filename {filename} успешно записан в БД", request.Filename);
        return 
            new CreateTrackModel(
                track.TrackId,
                track.Filename,
                track.InputKey,
                track.OutputKey,
                track.CreatedAt
            );
    }
}
