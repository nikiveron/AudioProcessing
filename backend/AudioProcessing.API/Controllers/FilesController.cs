using AudioProcessing.Application.Files.CreatePresignedUrl;
using MediatR;
using Microsoft.AspNetCore.Mvc;
using AudioProcessing.Application.Files.UploadFile;
using AudioProcessing.Application.Files.DownloadFile;
using AudioProcessing.Domain.Requests.FileUpload;

namespace AudioProcessing.API.Controllers;

/// <summary>
/// Контроллер для работы с файлами, предоставляющий конечные точки для получения presigned URL для загрузки в MinIO, загрузки файлов и скачивания файлов.
/// </summary>
/// <param name="mediator">Экземпляр посредника MediatR</param>
[ApiController]
[Route("api/files")]
public class FilesController(IMediator mediator) : ControllerBase
{
    private const string _inputPath = "input";
    private const string _outputPath = "output";

    /// <summary>
    /// Метод выдаёт presigned URL для загрузки в MinIO
    /// </summary>
    /// <param name="request">Объект запроса, содержащий имя файла для загрузки</param>
    /// <param name="cancellationToken">Токен отмены</param>
    /// <returns>Объект <see cref="IActionResult"/>, содержащий presigned URL для загрузки файла</returns>
    [HttpPost("presigned-upload")]
    public async Task<IActionResult> GetPresignedUrl([FromBody] FileUploadRequest request, CancellationToken cancellationToken)
    {
        return Ok(await mediator.Send(new CreatePresignedUrlCommand(request.Filename, _inputPath, _outputPath), cancellationToken));
    }

    /// <summary>
    /// Обрабатывает запросы на загрузку файла, принимая файл от клиента и инициируя процесс загрузки
    /// асинхронно.
    /// </summary>
    /// <remarks>Файл обрабатывается асинхронно. Максимально допустимый размер файла и поддерживаемые типы файлов
    /// могут ограничиваться конфигурацией сервера.</remarks>
    /// <param name="file">Файл для загрузки, передаваемый как данные формы. Не может быть null.</param>
    /// <param name="cancellationToken">Токен для отслеживания запросов на отмену. Передача отменённого токена попытается отменить операцию.</param>
    /// <returns>IActionResult, указывающий на результат операции загрузки. Возвращает 200 OK, если загрузка прошла успешно.</returns>
    [HttpPost("upload")]
    public async Task<IActionResult> UploadFile([FromForm] IFormFile file, CancellationToken cancellationToken)
    {
        return Ok(await mediator.Send(new UploadFileCommand(file), cancellationToken));
    }

    /// <summary>
    /// Инициирует скачивание файла по указанному ключу объекта.
    /// </summary>
    /// <remarks>Ответ включает соответствующий тип содержимого и имя файла для скачиваемого файла.
    /// Эта конечная точка обычно используется, чтобы позволить клиентам получать файлы по их ключу объекта.</remarks>
    /// <param name="objectKey">Уникальный идентификатор файла для скачивания. Не может быть null или пустым.</param>
    /// <param name="cancellationToken">Токен для отслеживания запросов на отмену.</param>
    /// <returns>IActionResult, который при выполнении возвращает содержимое файла в виде ответа для скачивания. Возвращает
    /// результат 404 Not Found, если файл не существует.</returns>
    [HttpGet("download")]
    public async Task<IActionResult> DownloadFile([FromQuery] string objectKey, CancellationToken cancellationToken)
    {
        var result = await mediator.Send(new DownloadFileQuery(objectKey), cancellationToken);
        return File(result.Stream, result.ContentType, result.Filename);
    }
}