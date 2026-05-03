using AudioProcessing.Application.Tracks.CreateTrack;
using AudioProcessing.Application.Tracks.GetTrackById;
using AudioProcessing.Domain.Requests.TracksController;
using MediatR;
using Microsoft.AspNetCore.Mvc;

namespace AudioProcessing.API.Controllers;

/// <summary>
/// Контроллер для управления треками, предоставляющий конечные точки для создания трека и получения информации о треке по его идентификатору.
/// </summary>
[ApiController]
[Route("api/tracks")]
public class TracksController(IMediator mediator) : ControllerBase
{
    /// <summary>
    /// Метод сохраняет информацию о треке в базу данных
    /// </summary>
    /// <param name="request"></param>
    /// <returns></returns>
    [HttpPost]
    public async Task<IActionResult> CreateTrack([FromBody] CreateTrackRequest request, CancellationToken cancelationToken)
    {
        return Ok(await mediator.Send(new CreateTrackCommand(request.Filename, request.InputKey, request.OutputKey), cancelationToken));
    }

    /// <summary>
    /// Метод возвращает информацию о треке по его идентификатору
    /// </summary>
    /// <param name="id">Идентификатор трека</param>
    /// <param name="cancelationToken">Токен отмены</param>
    /// <returns>Информация о треке</returns>
    [HttpGet("{id:guid}")]
    public async Task<IActionResult> GetTrackById(Guid id, CancellationToken cancelationToken)
    {
        return Ok(await mediator.Send(new GetTrackByIdQuery(id), cancelationToken));
    }
}