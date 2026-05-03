using AudioProcessing.Domain.Exceptions;
using AudioProcessing.Domain.Entities.Job;
using AudioProcessing.Infrastructure.Database.Repositories;
using MediatR;
using Microsoft.Extensions.Logging;
using System.Net;

namespace AudioProcessing.Application.Jobs.UpdateJob;

public record UpdateJobCommand(
    Guid JobId,
    JobStatus Status, 
    string OutputKey, 
    DateTime? StartedAt, 
    DateTime? FinishedAt
) : IRequest<UpdateJobModel>;

internal class UpdateJobHandler(
    ILogger<UpdateJobHandler> logger, 
    JobsRepository jobsRepository
) : IRequestHandler<UpdateJobCommand, UpdateJobModel>
{
    public async Task<UpdateJobModel> Handle(UpdateJobCommand request, CancellationToken cancellationToken)
    {
        logger.LogInformation("JobsController поступил PUT запрос для job с id {id}", request.JobId);
        try
        {
            var job = await jobsRepository.Read(request.JobId, cancellationToken);
            if (job == null)
            {
                logger.LogInformation("JobsController ошибка 404 для job с id {id}", request.JobId);
                throw new HttpErrorException("Ошибка! Job не был найден", HttpStatusCode.NotFound);
            }

            job.Status = request.Status != JobStatus.Null ? request.Status : job.Status;
            job.OutputKey = string.IsNullOrEmpty(request.OutputKey) ? job.OutputKey : request.OutputKey;
            job.StartedAt = request.StartedAt == null ? job.StartedAt : request.StartedAt;
            job.FinishedAt = request.FinishedAt == null ? job.FinishedAt : request.FinishedAt;

            await jobsRepository.Update(job, cancellationToken);

            logger.LogInformation("JobsController обновлены значения для job с id {id}", request.JobId);
            return new UpdateJobModel(
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
            logger.LogInformation("JobsController ошибка 500 для id {id}", request.JobId);
            throw new HttpErrorException($"Ошибка! {ex.Message}", HttpStatusCode.InternalServerError);
        }
    }
}
