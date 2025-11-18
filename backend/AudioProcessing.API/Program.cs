using AudioProcessing.Infrastructure.Context;
using AudioProcessing.Infrastructure.Storage;
using Confluent.Kafka;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Minio;
using Scalar.AspNetCore;
using System.Diagnostics;

var builder = WebApplication.CreateBuilder(args);
var configuration = builder.Configuration;

// --- Привязка настроек Minio (Options pattern)
builder.Services.Configure<MinioSettings>(configuration.GetSection("Minio"));

// --- DB: ожидаем ConnectionStrings:Postgres
var pgConn = configuration.GetConnectionString("Postgres");
if (string.IsNullOrWhiteSpace(pgConn))
{
    // информативная ошибка, чтобы понять проблему сразу
    Console.WriteLine("ERROR: ConnectionStrings:Postgres is not set. Check your .env or configuration.");
}

// Add services to the container.
builder.Services.AddOpenApi();
builder.Services.AddControllers();

// DbContext: если connection string пуст — UseNpgsql всё равно вызовет ошибку при миграции/подключении
builder.Services.AddDbContext<AppDbContext>(opts =>
    opts.UseNpgsql(pgConn ?? throw new InvalidOperationException("ConnectionStrings:Postgres is missing"),
        b => b.MigrationsAssembly("AudioProcessing.Infrastructure")));

// Kafka producer — читаем key "Kafka:BootstrapServers"
var kafkaBootstrap = configuration["Kafka:BootstrapServers"];
if (string.IsNullOrWhiteSpace(kafkaBootstrap))
{
    Console.WriteLine("WARNING: Kafka:BootstrapServers is empty. Producer won't be able to send messages.");
}
var producerConfig = new ProducerConfig { BootstrapServers = kafkaBootstrap };
builder.Services.AddSingleton<IProducer<Null, string>>(sp => new ProducerBuilder<Null, string>(producerConfig).Build());

// Регистрация Minio IMinioClient фабрично (чтобы валидировать конфигурацию в одном месте)
builder.Services.AddSingleton(sp =>
{
    var minioSettings = sp.GetRequiredService<IOptions<MinioSettings>>().Value;
    if (string.IsNullOrWhiteSpace(minioSettings.Endpoint))
        throw new InvalidOperationException("Minio:Endpoint is not configured. Set Minio:Endpoint in environment or appsettings.");

    // Создаём клиент (Minio .NET API)
    var builderClient = new Minio.MinioClient()
        .WithEndpoint(minioSettings.Endpoint)
        .WithCredentials(minioSettings.AccessKey, minioSettings.SecretKey);

    // Если указана secure = false, можно попытаться отключить ssl. (MinioClient API не всегда имеет WithSSL; оставим стандартную цепочку)
    var client = builderClient.Build();
    return client;
});

// MinioService должен получать IMinioClient и настройки
builder.Services.AddSingleton<MinioService>();

// Hosted services, healthchecks, etc.
builder.Services.AddHealthChecks();

var app = builder.Build();

// Выполнять миграцию и bucket-инициализацию безопасно: оборачиваем в try/catch
using (var scope = app.Services.CreateScope())
{
    var sp = scope.ServiceProvider;

    // миграции
    try
    {
        var db = sp.GetRequiredService<AppDbContext>();
        db.Database.Migrate();
    }
    catch (Exception ex)
    {
        Debug.WriteLine($"Database migration failed: {ex.Message}");
        Console.WriteLine($"Database migration failed: {ex.Message}");
    }

    // Ensure bucket (если Minio доступен)
    try
    {
        var minioService = sp.GetRequiredService<MinioService>();
        await minioService.EnsureBucketExistsAsync();
    }
    catch (Exception ex)
    {
        Debug.WriteLine($"MinIO initialization failed: {ex.Message}");
        Console.WriteLine($"MinIO initialization failed: {ex.Message}");
        // не пробрасываем — приложение продолжит работать (но без MinIO функционал будет ограничен)
    }
}

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();

    app.UseSwaggerUI(options =>
    {
        options.SwaggerEndpoint("/openapi/v1.json", "OpenAPI V1");
    });

    app.UseReDoc(options =>
    {
        options.SpecUrl("/openapi/v1.json");
    });

    app.MapScalarApiReference();
}

app.UseRouting();

// Для разработки можно временно отключить HttpsRedirect, если не настроены certs в контейнере
// app.UseHttpsRedirection();

app.MapHealthChecks("/api/health");
app.MapControllers();

app.Run();

record WeatherForecast(DateOnly Date, int TemperatureC, string? Summary)
{
    public int TemperatureF => 32 + (int)(TemperatureC / 0.5556);
}

