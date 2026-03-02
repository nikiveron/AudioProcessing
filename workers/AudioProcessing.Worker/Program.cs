using AudioProcessing.Worker.Services;

var builder = Host.CreateApplicationBuilder(args);

builder.Services.AddHostedService<JobConsumerService>();

var host = builder.Build();
host.Run();
