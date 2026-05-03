using AudioProcessing.Infrastructure.Database.Context;
using AudioProcessing.Infrastructure.Database.Repositories;
using AudioProcessing.Infrastructure.Storage;
using AudioProcessing.Worker.Services;
using AudioProcessing.Worker.Services.Interfaces;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Minio;

var builder = Host.CreateApplicationBuilder(args);
var services = builder.Services;

var connectionString = builder.Configuration.GetConnectionString("Postgres")
    ?? builder.Configuration["ConnectionStrings:Postgres"]
    ?? builder.Configuration["ConnectionStrings__Postgres"];

services.AddDbContext<AppDbContext>(opts =>
    opts.UseNpgsql(connectionString ?? throw new InvalidOperationException("ConnectionStrings:Postgres is missing"),
        b => b.MigrationsAssembly("AudioProcessing.Infrastructure")));

services.AddScoped<JobsRepository>();

services.Configure<MinioSettings>(builder.Configuration.GetSection("Minio"));

services.AddSingleton(sp =>
{
    var settings = sp.GetRequiredService<IOptions<MinioSettings>>().Value;

    var client = new MinioClient()
        .WithEndpoint(settings.Endpoint)
        .WithCredentials(settings.AccessKey, settings.SecretKey);

    if (!settings.Secure)
    {
        client = client.WithSSL(false);
    }

    return client.Build();
});

services.AddSingleton<MinioService>();

services.AddScoped<IJobPreparationService, JobPreparationService>();
services.AddSingleton<IKafkaPublisher, KafkaPublisher>();

services.AddHostedService<JobConsumerService>();

var host = builder.Build();
host.Run();
