using AudioProcessing.Domain.Exceptions;
using AudioProcessing.Infrastructure.Database.Repositories;
using MediatR;
using Microsoft.Extensions.Logging;
using System.Net;

namespace AudioProcessing.Application.Jobs.GetJobStatus;

public record GetJobStatusQuery(Guid JobId) : IRequest<GetJobStatusModel>;

public class GetJobStatusHandler(
    ILogger<GetJobStatusHandler> logger, 
    JobsRepository jobsRepository
) : IRequestHandler<GetJobStatusQuery, GetJobStatusModel>
{
    public async Task<GetJobStatusModel> Handle(GetJobStatusQuery request, CancellationToken cancellationToken)
    {
        logger.LogInformation("JobsController поступил GET запрос для job с id {id}", request.JobId);
        try
        {
            var job = await jobsRepository.Read(request.JobId, cancellationToken);
            if (job == null)
            {
                logger.LogInformation("JobsController ошибка 404 для job с id {id}", request.JobId);
                throw new HttpErrorException($"Ошибка! Job не найден", HttpStatusCode.NotFound);
            }

            logger.LogInformation("JobsController найден статус для job с id {id}", request.JobId);
            return new GetJobStatusModel(
                job.JobId,
                job.Status.ToString(),
                job.CreatedAt,
                job.StartedAt,
                job.FinishedAt,
                job.InputKey,
                job.OutputKey
            );
        }
        catch (Exception ex)
        {
            logger.LogInformation("JobsController ошибка 500 для job с id {id}", request.JobId);
            throw new HttpErrorException($"Ошибка! {ex.Message}", HttpStatusCode.InternalServerError);
        }
    }
}
