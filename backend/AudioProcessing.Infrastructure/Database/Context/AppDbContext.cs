using Microsoft.EntityFrameworkCore;
using AudioProcessing.Domain.Entities.Job;
using AudioProcessing.Domain.Entities.Track;


namespace AudioProcessing.Infrastructure.Database.Context;

public class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options)
{
    public DbSet<TrackEntity> Tracks { get; set; }
    public DbSet<JobEntity> Jobs { get; set; }
}