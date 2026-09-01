using AudioProcessing.API.Extensions;
using AudioProcessing.API.Middleware;
using AudioProcessing.API.Services;
using AudioProcessing.Application;
using Scalar.AspNetCore;

var builder = WebApplication.CreateBuilder(args);
var services = builder.Services;

builder.WebHost.ConfigureKestrel(options =>
{
    options.Limits.MaxRequestBodySize = 1000 * 1024 * 1024;
});

builder.Logging.ClearProviders();
builder.Logging.AddConsole();
builder.Logging.AddDebug();

services.AddApplicationServices(builder.Configuration);

services.AddSignalR();
services.AddMediatR(cfg =>
    cfg.RegisterServicesFromAssembly(typeof(AssemblyMarker).Assembly));

services.AddHealthChecks();
services.AddControllers();
services.AddOpenApi(options =>
{
    options.AddDocumentTransformer((document, context, cancellationToken) =>
    {
        document.Info = new()
        {
            Title = "AudioProcessing API",
            Version = "v1",
            Description = "API для обработки аудио"
        };
        return Task.CompletedTask;
    });
});


services.AddExceptionHandler<ExceptionHandler>();
services.AddProblemDetails();

var app = builder.Build();

app.UseExceptionHandler();

await app.InitializeInfrastructureAsync();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
    app.UseSwaggerUI(options =>
    {
        options.SwaggerEndpoint("/openapi/v1.json", "OpenAPI V1");
        options.RoutePrefix = "swagger";
    });
    app.UseReDoc(options =>
    {
        options.SpecUrl("/openapi/v1.json");
        options.RoutePrefix = "api-docs";
    });
    app.MapScalarApiReference();
}

app.UseCors("CorsPolicy");

app.MapHealthChecks("/api/health");
app.MapControllers();
app.MapHub<JobHub>("/hubs/jobs");

app.Run();
