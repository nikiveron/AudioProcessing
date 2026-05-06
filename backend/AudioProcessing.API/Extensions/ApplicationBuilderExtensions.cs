using AudioProcessing.Infrastructure.Database.Context;
using AudioProcessing.Infrastructure.Storage;
using Microsoft.EntityFrameworkCore;

namespace AudioProcessing.API.Extensions;

public static class ApplicationBuilderExtensions
{
    public static async Task InitializeInfrastructureAsync(this WebApplication app)
    {
        using var scope = app.Services.CreateScope();
        var logger = scope.ServiceProvider.GetRequiredService<ILoggerFactory>()
                                          .CreateLogger("Startup");

        try
        {
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            await db.Database.MigrateAsync();
            logger.LogInformation("Миграция применена к базе данных");
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Не удалось применить миграцию к базе данных");
        }

        try
        {
            var minio = scope.ServiceProvider.GetRequiredService<MinioService>();
            await minio.EnsureBucketExistsAsync(CancellationToken.None);
            logger.LogInformation("MinIO инициализирован");
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Не удалось инициализировать MinIO");
        }
    }
}
