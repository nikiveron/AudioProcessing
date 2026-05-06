using AudioProcessing.Worker.Extensions;

var builder = Host.CreateApplicationBuilder(args);

builder.Logging.ClearProviders();
builder.Logging.AddConsole();
builder.Logging.AddDebug();

builder.Services.AddWorkerInfrastructure(builder.Configuration);
builder.Services.AddWorkerApplication();

var host = builder.Build();
await host.RunAsync();