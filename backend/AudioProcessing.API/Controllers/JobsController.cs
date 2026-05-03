using Microsoft.AspNetCore.Mvc;
using MediatR;
using AudioProcessing.Application.Jobs.GetJobStatus;
using AudioProcessing.Application.Jobs.UpdateJob;
using AudioProcessing.Domain.Requests.JobsController;

namespace AudioProcessing.API.Controllers;

/// <summary>
/// Предоставляет HTTP API для получения и обновления статуса задач.
/// </summary>
/// <remarks>Контроллер реализует конечные точки для работы с задачами через шаблон Mediator. Все методы требуют
/// корректных идентификаторов задач. Контроллер предназначен для использования в RESTful API и поддерживает асинхронные
/// операции.</remarks>
/// <param name="mediator">Экземпляр посредника, используемый для отправки запросов и команд, связанных с задачами.</param>
[ApiController]
[Route("api/jobs")]
public class JobsController(IMediator mediator) : ControllerBase
{
    /// <summary>
    /// Метод возвращает статус задачи
    /// </summary>
    /// <param name="id"></param>
    /// <returns></returns>
    [HttpGet("{id:guid}")]
    public async Task<IActionResult> GetJobStatus([FromRoute] Guid id, CancellationToken cancellationToken)
    {
        return Ok(await mediator.Send(new GetJobStatusQuery(id), cancellationToken));
    }

    /// <summary>
    /// Метод обновляет статус задачи
    /// </summary>
    /// <param name="id">Идентификатор задачи</param>
    /// <param name="req">Объект запроса с новыми данными задачи</param>
    /// <param name="cancellationToken">Токен отмены</param>
    /// <returns>Объект <see cref="IActionResult"/>, содержащий обновлённые данные задачи</returns>
    [HttpPut("{id:guid}")]
    public async Task<IActionResult> UpdateJob(Guid id, UpdateJobRequest req, CancellationToken cancellationToken)
    {
        return Ok(await mediator.Send(new UpdateJobCommand(id, req.Status, req.OutputKey, req.StartedAt, req.FinishedAt), cancellationToken));
    }
}