using AudioProcessing.Domain.Entities.FileUpload;
using AudioProcessing.Infrastructure.Storage;
using Microsoft.AspNetCore.Mvc;

namespace AudioProcessing.API.Controllers;

[ApiController]
[Route("api/files")]
public class FilesController(MinioService minio) : ControllerBase
{
    private readonly MinioService _minio = minio;

    /// <summary>
    /// Метод выдаёт presigned URL для загрузки в MinIO
    /// </summary>
    /// <param name="request"></param>
    /// <returns></returns>
    [HttpPost("presigned-upload")]
    public IActionResult GetPresignedUrl([FromBody] FileUploadRequest request)
    {
        if (string.IsNullOrEmpty(request.Filename))
        {
            return BadRequest(new { message = "Error! Filename is required" });
        }

        try
        {
            string objectKey = $"uploads/{Guid.NewGuid()}_{request.Filename}";
            string url = _minio.PresignedPutObject(objectKey, 3600);

            return Ok(new
            {
                uploadUrl = url,
                objectKey
            });
        }
        catch (Exception ex)
        {
            return StatusCode(500, ex.Message);
        }
    }
}