using AudioProcessing.Domain.DTOs.FileUpload;
using AudioProcessing.Infrastructure.Storage;
using Microsoft.AspNetCore.Mvc;

namespace AudioProcessing.API.Controllers;

[ApiController]
[Route("api/files")]
public class FilesController(MinioService minio, ILogger<FilesController> logger) : ControllerBase
{
    private readonly MinioService _minio = minio;
    private readonly ILogger<FilesController> _logger = logger;
    private const string _inputPath = "input";
    private const string _outputPath = "output";

    /// <summary>
    /// Метод выдаёт presigned URL для загрузки в MinIO
    /// </summary>
    /// <param name="request"></param>
    /// <returns></returns>
    [HttpPost("presigned-upload")]
    public IActionResult GetPresignedUrl([FromBody] FileUploadRequest request)
    {
        _logger.LogInformation("FilesController поступил POST запрос для файла {request}", request.Filename);
        if (string.IsNullOrEmpty(request.Filename))
        {
            _logger.LogInformation("FilesController ошибка 400 для файла {request}", request.Filename);
            return BadRequest(new { message = "Error! Filename is required" });
        }

        try
        {
            var trackGuid = Guid.NewGuid();
            string inputKey = $"{_inputPath}/{trackGuid}_{request.Filename}";
            string outputKey = $"{_outputPath}/{trackGuid}_{request.Filename}";
            string url = _minio.PresignedPutObject(inputKey, 3600);

            _logger.LogInformation("FilesController место для файла {request} выделено", request.Filename);
            return Ok(new
            {
                uploadUrl = url,
                inputKey,
                outputKey
            });
        }
        catch (Exception ex)
        {
            _logger.LogInformation("FilesController ошибка 500 для файла {request}", request.Filename);
            return StatusCode(500, ex.Message);
        }
    }

    [HttpPost("upload")]
    public async Task<IActionResult> UploadFile([FromForm] IFormFile file, CancellationToken ct)
    {
        if (file == null || file.Length == 0)
            return BadRequest(new { message = "No file uploaded" });

        var trackGuid = Guid.NewGuid();
        string inputKey = $"input/{trackGuid}_{file.FileName}";
        string outputKey = $"output/{trackGuid}_{file.FileName}";

        try
        {
            using var stream = file.OpenReadStream();
            await _minio.UploadObjectAsync(inputKey, stream, file.ContentType, ct);

            _logger.LogInformation("File {Filename} uploaded to MinIO at {Key}", file.FileName, inputKey);

            return Ok(new
            {
                inputKey,
                outputKey
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error uploading file {Filename}", file.FileName);
            return StatusCode(500, new { message = ex.Message });
        }
    }

    [HttpGet("download")]
    public async Task<IActionResult> DownloadFile([FromQuery] string objectKey, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(objectKey))
            return BadRequest("objectKey is required");

        try
        {
            var stream = await _minio.GetObjectStreamAsync(objectKey, ct);
            var fileName = Path.GetFileName(objectKey);
            var ext = Path.GetExtension(fileName).ToLowerInvariant();

            var contentType = ext switch
            {
                ".wav" => "audio/wav",
                ".mp3" => "audio/mpeg",
                ".ogg" => "audio/ogg",
                _ => "application/octet-stream"
            };

            _logger.LogInformation("Downloading file {objectKey} from MinIO", objectKey);

            return File(stream, contentType, fileName);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error downloading file {objectKey}", objectKey);
            return NotFound();
        }
    }
}