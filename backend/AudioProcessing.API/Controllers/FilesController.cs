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
            string objectKey = $"uploads/{Guid.NewGuid()}_{request.Filename}";
            string url = _minio.PresignedPutObject(objectKey, 3600);

            _logger.LogInformation("FilesController место для файла {request} выделено", request.Filename);
            return Ok(new
            {
                uploadUrl = url,
                objectKey
            });
        }
        catch (Exception ex)
        {
            _logger.LogInformation("FilesController ошибка 500 для файла {request}", request.Filename);
            return StatusCode(500, ex.Message);
        }
    }
}