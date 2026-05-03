using AudioProcessing.Application.Process.StartProcess;
using AudioProcessing.Domain;
using AudioProcessing.Domain.Requests.Process;
using MediatR;
using Microsoft.AspNetCore.Mvc;
namespace AudioProcessing.API.Controllers;

/// <summary>
/// Контроллер для запуска обработки аудио. Подготавливает данные и отправляет сообщение в Kafka.
/// </summary>
/// <param name="mediator">Экземпляр посредника MediatR</param>
[ApiController]
[Route("api/process")]
public class ProcessController(IMediator mediator) : Controller
{
    private readonly string _outputTopic = KafkaTopics.JobCreated;

    /// <summary>
    /// Принимает параметры (fileKey, instrument), создаёт запись Job в БД и публикует сообщение в Kafka
    /// </summary>
    /// <param name="req"></param>
    /// <returns></returns>
    [HttpPost]
    public async Task<IActionResult> StartProcess([FromBody] ProcessRequestDto req, CancellationToken cancellationToken)
    {
        return Ok(await mediator.Send(new StartProcessCommand(req.TrackId, req.Instrument, _outputTopic), cancellationToken));
    }
}
