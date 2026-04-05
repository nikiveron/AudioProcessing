using AudioProcessing.Infrastructure.Storage;
using Microsoft.AspNetCore.Mvc;

namespace AudioProcessing.API.Controllers;

[ApiController]
[Route("api/health")]
public class HealthController : ControllerBase
{
    private readonly MinioService _minio;
    public HealthController(MinioService minio) { _minio = minio; }

    [HttpGet]
    public async Task<IActionResult> Get(CancellationToken ct)
    {
        try
        {
            await _minio.EnsureBucketExistsAsync(ct);
            return Ok(new { status = "ok" });
        }
        catch (Exception ex)
        {
            return StatusCode(500, ex.Message);
        }
    }
}