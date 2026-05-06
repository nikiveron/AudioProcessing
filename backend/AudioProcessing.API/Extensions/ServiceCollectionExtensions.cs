using AudioProcessing.API.Services;
using AudioProcessing.API.Services.Interfaces;
using AudioProcessing.Domain.Settings;
using AudioProcessing.Infrastructure.Database.Context;
using AudioProcessing.Infrastructure.Database.Repositories;
using AudioProcessing.Infrastructure.Storage;
using Confluent.Kafka;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Minio;

namespace AudioProcessing.API.Extensions;

public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddApplicationServices(this IServiceCollection services, IConfiguration config)
    {
        services.AddServices();
        services.AddKafka(config);
        services.AddMinio(config);
        services.AddDatabase(config);
        services.AddCorsConfig(config);

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

    private static IServiceCollection AddServices(this IServiceCollection services)
    {
        services.AddScoped<JobsRepository>();
        services.AddScoped<TracksRepository>();
        services.AddScoped<IJobStatusService, JobStatusService>();
        services.AddScoped<IJobNotifier, SignalRJobNotifier>();

        return services;
    }

    private static IServiceCollection AddKafka(this IServiceCollection services, IConfiguration config)
    {
        services.AddOptions<KafkaSettings>()
            .Bind(config.GetSection(KafkaSettings.Section))
            .ValidateDataAnnotations()
            .ValidateOnStart();

        services.AddSingleton(sp =>
        {
            var settings = sp.GetRequiredService<IOptions<KafkaSettings>>().Value;
            var producerConfig = new ProducerConfig
            {
                BootstrapServers = settings.BootstrapServers
            };

            return new ProducerBuilder<Null, string>(producerConfig).Build();
        });

        services.AddHostedService<JobStatusConsumer>();

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

        services.AddSingleton<MinioService>();

        return services;
    }

    private static IServiceCollection AddCorsConfig(this IServiceCollection services, IConfiguration config)
    {
        services.AddOptions<CorsSettings>()
            .Bind(config.GetSection(CorsSettings.Section));

        services.AddCors(options =>
        {
            options.AddPolicy("CorsPolicy", policy =>
            {
                var sp = services.BuildServiceProvider();
                var cors = sp.GetRequiredService<IOptions<CorsSettings>>().Value;

                policy.WithOrigins(cors.AllowedOrigins)
                      .AllowAnyMethod()
                      .AllowAnyHeader()
                      .AllowCredentials();
            });
        });

        return services;
    }
}
