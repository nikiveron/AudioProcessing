using AudioProcessing.Domain.DTOs.TracksController;
using AudioProcessing.Domain.Entities.Track;
using AudioProcessing.Infrastructure.Repositories;
using AudioProcessing.Infrastructure.Storage;
using Microsoft.AspNetCore.Mvc;

namespace AudioProcessing.API.Controllers;

[ApiController]
[Route("api/tracks")]
public class TracksController : ControllerBase
{
    private readonly TracksRepository _tracksRepository;
    private readonly MinioService _minio;
    private readonly ILogger _logger;   

    public TracksController(TracksRepository tracksRepository, MinioService minio, ILogger<TracksController> logger)
    {
        _tracksRepository = tracksRepository;
        _minio = minio;
        _logger = logger;
    }

    /// <summary>
    /// Метод сохраняет информацию о треке в базу данных
    /// </summary>
    /// <param name="req"></param>
    /// <returns></returns>
    [HttpPost]
    public async Task<IActionResult> CreateTrack([FromBody] CreateTrackRequest req, CancellationToken ct)
    {
        _logger.LogInformation("TracksController поступил POST запрос для Filename {filename}", req.Filename);
        // проверяем полученные данные
        if (string.IsNullOrWhiteSpace(req.Filename) || string.IsNullOrWhiteSpace(req.InputKey) || string.IsNullOrWhiteSpace(req.OutputKey))
        {
            string exception = "Filename, OutputKey и InputKey обязательные параметры";
            _logger.LogInformation("TracksController ошибка 400 для Filename {filename}: {exception}", req.Filename, exception);
            return BadRequest(new { message = exception });
        }

        // проверяем существует ли файл в minio
        bool exists = await _minio.ObjectExistsAsync(req.InputKey, ct);
        if (!exists)
        {
            string exception = "Файл не был найден в хранилище Minio";
            _logger.LogInformation("TracksController ошибка 400 для Filename {filename}: {exception}", req.Filename, exception);
            return BadRequest(exception);
        }

        // Проверяем, не создан ли уже Track
        bool alreadyExists = _tracksRepository.ReadList().Any(t => t.InputKey == req.InputKey);

        if (alreadyExists)
        {
            string exception = "Трек уже существует в базе";
            _logger.LogInformation("TracksController ошибка 409 для Filename {filename}: {exception}", req.Filename, exception);
            return Conflict(new { message = exception });
        }

        var track = new TrackEntity
        {
            TrackId = Guid.NewGuid(),
            Filename = req.Filename,
            InputKey = req.InputKey,
            OutputKey = req.OutputKey,
            CreatedAt = DateTime.UtcNow
        };

        await _tracksRepository.Create(track, ct);

        _logger.LogInformation("TracksController трек Filename {filename} успешно записан в БД", req.Filename);
        return CreatedAtAction(
            nameof(GetTrackById),
            new { id = track.TrackId },
            new
            {
                trackId = track.TrackId,
                filename = track.Filename,
                inputKey = track.InputKey,
                outputKey = req.OutputKey,
                createdAt = track.CreatedAt
            });
    }

    [HttpGet("{id:guid}")]
    public async Task<IActionResult> GetTrackById(Guid id, CancellationToken ct)
    {
        _logger.LogInformation("TracksController поступил GET запрос для id {id}", id);
        var track = await _tracksRepository.Read(id, ct);
        if (track == null)
        {
            _logger.LogInformation("TracksController ошибка 404 для id {id}", id);
            return NotFound();
        }

        _logger.LogInformation("TracksController трек с id {id} успешно найден", id);
        return Ok(track);
    }
}