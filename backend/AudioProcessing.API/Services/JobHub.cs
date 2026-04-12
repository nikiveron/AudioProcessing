using Microsoft.AspNetCore.SignalR;

namespace AudioProcessing.API.Services;

public class JobHub : Hub
{
    public async Task SubscribeToJob(string outputKey)
    {
        await Groups.AddToGroupAsync(Context.ConnectionId, outputKey);
    }
}
