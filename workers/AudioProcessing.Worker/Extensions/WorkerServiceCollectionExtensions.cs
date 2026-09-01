using AudioProcessing.Domain.Settings;
using AudioProcessing.Infrastructure.Database.Context;
using AudioProcessing.Infrastructure.Database.Repositories;
using AudioProcessing.Infrastructure.Database.Repositories.Interfaces;
using AudioProcessing.Infrastructure.Storage;
using AudioProcessing.Worker.Services;
using AudioProcessing.Worker.Services.Interfaces;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Minio;

namespace AudioProcessing.Worker.Extensions;

public static class WorkerServiceCollectionExtensions
{
    public static IServiceCollection AddWorkerInfrastructure(this IServiceCollection services, IConfiguration config)
    {
        services.AddDatabase(config);
        services.AddMinio(config);
        services.AddKafka(config);

        return services;
    }

    public static IServiceCollection AddWorkerApplication(this IServiceCollection services)
    {
        services.AddScoped<IJobsRepository, JobsRepository>();
        services.AddScoped<IJobPreparationService, JobPreparationService>();

        services.AddSingleton<IKafkaPublisher, KafkaPublisher>();
        services.AddHostedService<JobConsumerService>();

        return services;
    }

    private static IServiceCollection AddDatabase(this IServiceCollection services, IConfiguration config)
    {
        services.AddDbContext<AppDbContext>(opts =>
            opts.UseNpgsql(
                config.GetConnectionString("Postgres"),
                b => b.MigrationsAssembly("AudioProcessing.Infrastructure")));

        return services;
    }

    private static IServiceCollection AddKafka(this IServiceCollection services, IConfiguration config)
    {
        services.AddOptions<KafkaSettings>()
            .Bind(config.GetSection(KafkaSettings.Section))
            .ValidateDataAnnotations()
            .ValidateOnStart();

        return services;
    }

    private static IServiceCollection AddMinio(this IServiceCollection services, IConfiguration config)
    {
        services.AddOptions<MinioSettings>()
            .Bind(config.GetSection("Minio"))
            .ValidateDataAnnotations()
            .ValidateOnStart();

        services.AddSingleton(sp =>
        {
            var settings = sp.GetRequiredService<IOptions<MinioSettings>>().Value;

            return new MinioClient()
                .WithEndpoint(settings.Endpoint)
                .WithCredentials(settings.AccessKey, settings.SecretKey)
                .Build();
        });

        services.AddSingleton<IMinioService, MinioService>();

        return services;
    }
}
