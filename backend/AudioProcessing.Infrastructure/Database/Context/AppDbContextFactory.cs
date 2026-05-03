using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace AudioProcessing.Infrastructure.Database.Context;

public class AppDbContextFactory : IDesignTimeDbContextFactory<AppDbContext>
{
    public AppDbContext CreateDbContext(string[] args)
    {
        var opts = new DbContextOptionsBuilder<AppDbContext>();

        var connectionString = "Host=localhost;Port=5432;Database=audio_db;Username=audio;Password=audio123";

        opts.UseNpgsql(connectionString);

        return new AppDbContext(opts.Options);
    }
}
