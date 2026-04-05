using AudioProcessing.Domain.Entities.Job;
using AudioProcessing.Infrastructure.Context;

namespace AudioProcessing.Infrastructure.Repositories;

public class JobsRepository
{
    private AppDbContext _db;

    public JobsRepository(AppDbContext db)
    {
        _db = db;
    }

    public async Task<Guid> Create(JobEntity jobEntity, CancellationToken ct)
    {
        if (jobEntity == null || string.IsNullOrEmpty(jobEntity.InputKey))
        {
            throw new ArgumentNullException(nameof(jobEntity));
        }

        _db.Jobs.Add(jobEntity);
        await _db.SaveChangesAsync(ct);
        return jobEntity.JobId;
    }


    public async Task<JobEntity?> Read(Guid id, CancellationToken ct)
    {
        return await _db.Jobs.FindAsync([id, ct], cancellationToken: ct);
    }

    public async Task Update(JobEntity jobEntity, CancellationToken ct)
    {
        if (jobEntity == null || string.IsNullOrEmpty(jobEntity.InputKey))
        {
            throw new ArgumentNullException(nameof(jobEntity));
        }

        var job = await _db.Jobs.FindAsync([jobEntity.JobId, ct], cancellationToken: ct);
        job = new JobEntity { JobId = jobEntity.JobId, TrackId = jobEntity.TrackId, Status = jobEntity.Status, InputKey = jobEntity.InputKey, OutputKey = jobEntity.OutputKey, CreatedAt = jobEntity.CreatedAt, StartedAt = jobEntity.StartedAt, FinishedAt = jobEntity.FinishedAt };
        await _db.SaveChangesAsync(ct);
    }

    public async Task Delete(Guid id, CancellationToken ct)
    {
        var job = await _db.Jobs.FindAsync([id, ct], cancellationToken: ct);
        if (job != null)
        {
            _db.Jobs.Remove(job);
        }
    }
}