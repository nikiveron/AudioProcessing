using AudioProcessing.Infrastructure.Storage;
using Microsoft.AspNetCore.Mvc;

namespace AudioProcessing.API.Controllers;

/// <summary>
/// Контроллер для проверки состояния сервиса MinIO. Предоставляет конечную точку для проверки доступности MinIO и существования необходимого бакета.
/// </summary>
/// <param name="minio">Сервис MinIO для проверки состояния</param>
[ApiController]
[Route("api/health")]
public class HealthController(IMinioService minio) : ControllerBase
{
    /// <summary>
    /// Метод проверяет доступность MinIO и существование бакета. Если бакет не существует, пытается его создать.
    /// </summary>
    /// <param name="ct">Токен отмены</param>
    /// <returns>Статус доступности сервиса MinIO</returns>
    [HttpGet]
    public async Task<IActionResult> Get(CancellationToken ct)
    {
        try
        {
            await minio.EnsureBucketExistsAsync(ct);
            return Ok(new { status = "ok" });
        }
        catch (Exception ex)
        {
            return StatusCode(500, ex.Message);
        }
    }
}