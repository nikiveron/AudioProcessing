using AudioProcessing.Domain.Entities.Job;
using AudioProcessing.Infrastructure.Database.Context;

namespace AudioProcessing.Infrastructure.Database.Repositories;

public class JobsRepository(AppDbContext db)
{
    public async Task<Guid> Create(JobEntity jobEntity, CancellationToken ct)
    {
        if (jobEntity == null || string.IsNullOrEmpty(jobEntity.InputKey))
        {
            throw new ArgumentNullException(nameof(jobEntity));
        }

        db.Jobs.Add(jobEntity);
        await db.SaveChangesAsync(ct);
        return jobEntity.JobId;
    }


    public async Task<JobEntity?> Read(Guid id, CancellationToken ct)
    {
        return await db.Jobs.FindAsync([id], ct);
    }

    public async Task Update(JobEntity jobEntity, CancellationToken ct)
    {
        if (jobEntity == null || string.IsNullOrEmpty(jobEntity.InputKey))
        {
            throw new ArgumentNullException(nameof(jobEntity));
        }

        var job = await db.Jobs.FindAsync([jobEntity.JobId], ct);
        if (job != null)
        {
            job.JobId = jobEntity.JobId;
            job.TrackId = jobEntity.TrackId;
            job.Status = jobEntity.Status;
            job.InputKey = jobEntity.InputKey;
            job.OutputKey = jobEntity.OutputKey;
            job.CreatedAt = jobEntity.CreatedAt;
            job.StartedAt = jobEntity.StartedAt;
            job.FinishedAt = jobEntity.FinishedAt;

            await db.SaveChangesAsync(ct);
        }
    }

    public async Task Delete(Guid id, CancellationToken ct)
    {
        var job = await db.Jobs.FindAsync([id], ct);
        if (job != null)
        {
            db.Jobs.Remove(job);
            await db.SaveChangesAsync(ct);
        }
    }
}