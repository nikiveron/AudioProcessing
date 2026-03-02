using Microsoft.EntityFrameworkCore;
using AudioProcessing.Domain.Entities.Job;
using AudioProcessing.Domain.Entities.Track;
using AudioProcessing.Domain.Entities.User;
using AudioProcessing.Domain.Entities.Project;


namespace AudioProcessing.Infrastructure.Context;
public class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options)
{
    public DbSet<TrackEntity> Tracks { get; set; }
    public DbSet<JobEntity> Jobs { get; set; }
    public DbSet<UserEntity> Users { get; set; }
    public DbSet<ProjectEntity> Projects { get; set; }
}