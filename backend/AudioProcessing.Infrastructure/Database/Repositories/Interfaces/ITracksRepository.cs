using AudioProcessing.Domain.Entities.Track;

namespace AudioProcessing.Infrastructure.Database.Repositories.Interfaces;

public interface ITracksRepository
{
    public Task<Guid> Create(TrackEntity trackEntity, CancellationToken ct);
    public Task<TrackEntity?> Read(Guid id, CancellationToken ct);
    public Task Update(TrackEntity trackEntity, CancellationToken ct);
    public Task Delete(Guid id, CancellationToken ct);
    public Task<List<TrackEntity>> ReadList(CancellationToken ct);
}
