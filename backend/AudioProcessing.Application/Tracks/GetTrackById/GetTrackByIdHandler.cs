using AudioProcessing.Domain;
using AudioProcessing.Infrastructure.Database.Repositories;
using MediatR;
using Microsoft.Extensions.Logging;
using System.Net;

namespace AudioProcessing.Application.Tracks.GetTrackById;

public record GetTrackByIdQuery(Guid TrackId) : IRequest<GetTrackByIdModel>;

public class GetTrackByIdHandler(
    ILogger<GetTrackByIdHandler> logger,
    TracksRepository tracksRepository
) : IRequestHandler<GetTrackByIdQuery, GetTrackByIdModel>
{
    public async Task<GetTrackByIdModel> Handle(GetTrackByIdQuery request, CancellationToken cancellationToken)
    {
        logger.LogInformation("TracksController поступил GET запрос для id {id}", request.TrackId);
        var track = await tracksRepository.Read(request.TrackId, cancellationToken);
        if (track == null)
        {
            logger.LogInformation("TracksController ошибка 404 для id {id}", request.TrackId);
            throw new HttpErrorException($"Ошибка! Трек с указанным id {request.TrackId} не найден", HttpStatusCode.NotFound);
        }

        logger.LogInformation("TracksController трек с id {id} успешно найден", request.TrackId);
        return new GetTrackByIdModel(track.TrackId, track.InputKey, track.OutputKey, track.Filename, track.CreatedAt, track.DeletedAt);
    }
}
