using AudioProcessing.Domain.Entities.Job;

namespace AudioProcessing.Infrastructure.Database.Repositories.Interfaces;

public interface IJobsRepository
{
    public Task<Guid> Create(JobEntity jobEntity, CancellationToken ct);
    public Task<JobEntity?> Read(Guid id, CancellationToken ct);
    public Task Update(JobEntity jobEntity, CancellationToken ct);
    public Task Delete(Guid id, CancellationToken ct);
}
