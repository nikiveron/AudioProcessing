using AudioProcessing.Domain.Entities.Track;
using AudioProcessing.Domain.Exceptions;
using AudioProcessing.Infrastructure.Database.Repositories;
using AudioProcessing.Infrastructure.Database.Repositories.Interfaces;
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
    ITracksRepository tracksRepository,
    IMinioService minio
) : IRequestHandler<CreateTrackCommand, CreateTrackModel>
{
    public async Task<CreateTrackModel> Handle(CreateTrackCommand request, CancellationToken cancellationToken)
    {
        logger.LogInformation("TracksController поступил POST запрос для Filename {filename}", request.Filename);
        // проверяем полученные данные
        if (string.IsNullOrWhiteSpace(request.Filename) || string.IsNullOrWhiteSpace(request.InputKey) || string.IsNullOrWhiteSpace(request.OutputKey))
        {
            logger.LogInformation("TracksController ошибка 400 для Filename {filename}: {exception}", request.Filename, ExceptionDictionary.MissingRequiredFields);
            throw new HttpErrorException(ExceptionDictionary.MissingRequiredFields, HttpStatusCode.BadRequest);
        }

        // проверяем существует ли файл в minio
        bool exists = await minio.ObjectExistsAsync(request.InputKey, cancellationToken);
        if (!exists)
        {
            logger.LogInformation("TracksController ошибка 404 для Filename {filename}: {exception}", request.Filename, ExceptionDictionary.FileNotFoundInMinio);
            throw new HttpErrorException(ExceptionDictionary.FileNotFoundInMinio, HttpStatusCode.NotFound);
        }

        var track = new TrackEntity
        {
            TrackId = Guid.NewGuid(),
            Filename = request.Filename,
            InputKey = request.InputKey,
            OutputKey = request.OutputKey,
            CreatedAt = DateTime.UtcNow
        };

        try
        {
            await tracksRepository.Create(track, cancellationToken);
        }
        catch (ArgumentNullException)
        {
            throw new HttpErrorException(ExceptionDictionary.NullTrackCreationFailed, HttpStatusCode.BadRequest);
        }
        catch
        {
            throw new HttpErrorException(ExceptionDictionary.TrackCreationFailed, HttpStatusCode.InternalServerError);
        }

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
