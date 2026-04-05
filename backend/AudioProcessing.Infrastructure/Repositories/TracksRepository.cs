using AudioProcessing.Domain.Entities.Track;
using AudioProcessing.Infrastructure.Context;

namespace AudioProcessing.Infrastructure.Repositories;

public class TracksRepository
{
    private readonly AppDbContext _db;

    public TracksRepository(AppDbContext db)
    {
        _db = db;
    }

    public async Task<Guid> Create(TrackEntity trackEntity, CancellationToken ct)
    {
        if (trackEntity == null || string.IsNullOrEmpty(trackEntity.InputKey) || string.IsNullOrEmpty(trackEntity.Filename))
        {
            throw new ArgumentNullException(nameof(trackEntity));
        }

        _db.Tracks.Add(trackEntity);
        await _db.SaveChangesAsync(ct);
        return trackEntity.TrackId;
    }

    public async Task<TrackEntity?> Read(Guid id, CancellationToken ct)
    {
        return await _db.Tracks.FindAsync([id, ct], cancellationToken: ct);
    }

    public async Task Update(TrackEntity trackEntity, CancellationToken ct)
    {
        if (trackEntity == null || string.IsNullOrEmpty(trackEntity.InputKey) || string.IsNullOrEmpty(trackEntity.Filename))
        {
            throw new ArgumentNullException(nameof(trackEntity));
        }

        var track = await _db.Tracks.FindAsync([trackEntity.TrackId, ct], cancellationToken: ct);
        if (track != null)
        {
            track = new TrackEntity { TrackId = trackEntity.TrackId, InputKey = trackEntity.InputKey, Filename = trackEntity.Filename, CreatedAt = trackEntity.CreatedAt, DeletedAt = trackEntity.DeletedAt };
            await _db.SaveChangesAsync(ct);
        }
    }

    public async Task Delete(Guid id, CancellationToken ct)
    {
        var track = await _db.Tracks.FindAsync([id, ct], cancellationToken: ct);
        if (track != null)
        {
            _db.Tracks.Remove(track);
        }
    }

    public List<TrackEntity> ReadList()
    {
        return [.. _db.Tracks];
    }
}
