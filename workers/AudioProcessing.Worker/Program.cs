using AudioProcessing.Infrastructure.Context;
using AudioProcessing.Infrastructure.Repositories;
using AudioProcessing.Infrastructure.Storage;
using AudioProcessing.Worker.Services;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Minio;

var builder = Host.CreateApplicationBuilder(args);

var connectionString = builder.Configuration.GetConnectionString("Postgres")
    ?? builder.Configuration["ConnectionStrings:Postgres"]
    ?? builder.Configuration["ConnectionStrings__Postgres"];

builder.Services.AddDbContext<AppDbContext>(opts =>
    opts.UseNpgsql(connectionString ?? throw new InvalidOperationException("ConnectionStrings:Postgres is missing"),
        b => b.MigrationsAssembly("AudioProcessing.Infrastructure")));

builder.Services.AddScoped<JobsRepository>();

builder.Services.Configure<MinioSettings>(builder.Configuration.GetSection("Minio"));

builder.Services.AddSingleton(sp =>
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

builder.Services.AddSingleton<MinioService>();

builder.Services.AddHostedService<JobConsumerService>();

var host = builder.Build();
host.Run();
