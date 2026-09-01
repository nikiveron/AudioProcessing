using AudioProcessing.Application.Tracks.GetTrackById;
using AudioProcessing.Domain.Entities.Track;
using AudioProcessing.Domain.Exceptions;
using AudioProcessing.Infrastructure.Database.Repositories.Interfaces;
using Microsoft.Extensions.Logging;
using Moq;
using System.Net;
using static Microsoft.EntityFrameworkCore.DbLoggerCategory.Database;

namespace UnitTests.Application.Tracks;

public class GetTrackByIdHandlerTests
{
    private readonly Mock<ILogger<GetTrackByIdHandler>> _loggerMock = new();
    private readonly Mock<ITracksRepository> _tracksRepositoryMock = new();
    private TrackEntity ExistingTrackEntity { get; init; }

    public GetTrackByIdHandlerTests()
    {
        ExistingTrackEntity = new TrackEntity()
        {
            TrackId = Guid.NewGuid(),
            Filename = "existing-file-name",
            InputKey = "input/existing-input-key.wav",
            OutputKey = "output/existing-output-key.wav",
            CreatedAt = DateTime.UtcNow
        };

        _tracksRepositoryMock
            .Setup(t => t.Read(ExistingTrackEntity.TrackId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(ExistingTrackEntity);
    }

    [Fact]
    public async Task GetTrackByIdHandler_TrackExists_Success()
    {
        // Arrange
        var query = new GetTrackByIdQuery(ExistingTrackEntity.TrackId);
        var handler = new GetTrackByIdHandler(_loggerMock.Object, _tracksRepositoryMock.Object);

        // Act
        var response = await handler.Handle(query, CancellationToken.None);

        // Assert
        Assert.Equal(ExistingTrackEntity.Filename, response.Filename);
        Assert.Equal(ExistingTrackEntity.InputKey, response.InputKey);
        Assert.Equal(ExistingTrackEntity.OutputKey, response.OutputKey);
    }

    [Fact]
    public async Task GetTrackByIdHandler_TrackNotFoundInDatabase_ThrowsHttpErrorException()
    {
        // Arrange
        _tracksRepositoryMock
            .Setup(t => t.Read(ExistingTrackEntity.TrackId, It.IsAny<CancellationToken>()))
            .ReturnsAsync((TrackEntity?)null);

        var query = new GetTrackByIdQuery(ExistingTrackEntity.TrackId);
        var handler = new GetTrackByIdHandler(_loggerMock.Object, _tracksRepositoryMock.Object);

        // Act 
        var exception = await Assert.ThrowsAsync<HttpErrorException>(() => handler.Handle(query, CancellationToken.None));

        // Assert
        Assert.Equal(ExceptionDictionary.TrackNotFoundInDatabase, exception.ErrorMessage);
        Assert.Equal(HttpStatusCode.NotFound, exception.HttpStatusCode);
    }
}
