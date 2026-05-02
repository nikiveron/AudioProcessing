using AudioProcessing.Domain.Entities.Track;
using AudioProcessing.Infrastructure.Database.Context;
using Microsoft.EntityFrameworkCore;

namespace AudioProcessing.Infrastructure.Database.Repositories;

public class TracksRepository(AppDbContext db)
{
    public async Task<Guid> Create(TrackEntity trackEntity, CancellationToken ct)
    {
        if (trackEntity == null || string.IsNullOrEmpty(trackEntity.InputKey) || string.IsNullOrEmpty(trackEntity.Filename))
        {
            throw new ArgumentNullException(nameof(trackEntity));
        }

        db.Tracks.Add(trackEntity);
        await db.SaveChangesAsync(ct);
        return trackEntity.TrackId;
    }

    public async Task<TrackEntity?> Read(Guid id, CancellationToken ct)
    {
        return await db.Tracks.FindAsync([id], ct);
    }

    public async Task Update(TrackEntity trackEntity, CancellationToken ct)
    {
        if (trackEntity == null || string.IsNullOrEmpty(trackEntity.InputKey) || string.IsNullOrEmpty(trackEntity.Filename))
        {
            throw new ArgumentNullException(nameof(trackEntity));
        }

        var track = await db.Tracks.FindAsync([trackEntity.TrackId], ct);
        if (track != null)
        {
            track.InputKey = trackEntity.InputKey;
            track.Filename = trackEntity.Filename;
            track.DeletedAt = trackEntity.DeletedAt;
            await db.SaveChangesAsync(ct);
        }
    }

    public async Task Delete(Guid id, CancellationToken ct)
    {
        var track = await db.Tracks.FindAsync([id], ct);
        if (track != null)
        {
            db.Tracks.Remove(track);
            await db.SaveChangesAsync(ct);
        }
    }

    public async Task<List<TrackEntity>> ReadList(CancellationToken ct)
    {
        return await db.Tracks.ToListAsync(ct);
    }
}
