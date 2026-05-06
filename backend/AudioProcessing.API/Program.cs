using AudioProcessing.API.Extensions;
using AudioProcessing.API.Middleware;
using AudioProcessing.API.Services;
using AudioProcessing.Application;
using Scalar.AspNetCore;

var builder = WebApplication.CreateBuilder(args);
var services = builder.Services;

builder.Logging.ClearProviders();
builder.Logging.AddConsole();
builder.Logging.AddDebug();

services.AddApplicationServices(builder.Configuration);

services.AddSignalR();
services.AddMediatR(cfg =>
    cfg.RegisterServicesFromAssembly(typeof(AssemblyMarker).Assembly));

services.AddHealthChecks();
services.AddControllers();
services.AddOpenApi();

services.AddExceptionHandler<ExceptionHandler>();
services.AddProblemDetails();

var app = builder.Build();

app.UseExceptionHandler();

await app.InitializeInfrastructureAsync();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
    app.UseSwaggerUI(o => o.SwaggerEndpoint("/openapi/v1.json", "OpenAPI V1"));
    app.UseReDoc(o => o.SpecUrl("/openapi/v1.json"));
    app.MapScalarApiReference();
}

app.UseCors("CorsPolicy");

app.MapHealthChecks("/api/health");
app.MapControllers();
app.MapHub<JobHub>("/hubs/jobs");

app.Run();
