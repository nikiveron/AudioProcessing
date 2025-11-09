using AudioProcessing.Worker;

var builder = Host.CreateApplicationBuilder(args);
builder.Services.AddHostedService<Worker>();

builder.Services.AddHostedService<AudioProcessing.Worker.Services.JobConsumerService>();

var host = builder.Build();
host.Run();
