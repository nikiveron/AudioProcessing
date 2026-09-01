using AudioProcessing.Application.Tracks.CreateTrack;
using AudioProcessing.Domain.Entities.Track;
using AudioProcessing.Domain.Exceptions;
using AudioProcessing.Infrastructure.Database.Repositories.Interfaces;
using AudioProcessing.Infrastructure.Storage;
using Microsoft.Extensions.Logging;
using Moq;
using System.Net;

namespace UnitTests.Application.Tracks;

public class CreateTrackHandlerTests
{
    private readonly Mock<ILogger<CreateTrackHandler>> _loggerMock = new();
    private readonly Mock<ITracksRepository> _tracksRepositoryMock = new();
    private readonly Mock<IMinioService> _minioServiceMock = new();
    private readonly Guid _defaultTrackGuid = Guid.NewGuid();
    private const string _defaultFileName = "file-name";
    private const string _defaultInputKey = "input/input-key.wav";
    private const string _defaultOutputKey = "output/output-key.wav";

    public CreateTrackHandlerTests()
    {
        _tracksRepositoryMock
            .Setup(t => t.Create(It.IsAny<TrackEntity>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(_defaultTrackGuid);
        _minioServiceMock
            .Setup(m => m.ObjectExistsAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(true);
    }

    [Fact]
    public async Task CreateTrackHandler_CreatedTrack_Success()
    {
        // Arrange
        var command = new CreateTrackCommand(_defaultFileName, _defaultInputKey, _defaultOutputKey);
        var handler = new CreateTrackHandler(_loggerMock.Object, _tracksRepositoryMock.Object, _minioServiceMock.Object);

        // Act
        var response = await handler.Handle(command, CancellationToken.None);

        // Assert
        Assert.Equal(_defaultFileName, response.Filename);
        Assert.Equal(_defaultInputKey, response.InputKey);
        Assert.Equal(_defaultOutputKey, response.OutputKey);
    }

    [Theory]
    [InlineData("", _defaultInputKey, _defaultOutputKey)]
    [InlineData(_defaultFileName, "", _defaultOutputKey)]
    [InlineData(_defaultFileName, _defaultInputKey, "")]
    public async Task CreateTrackHandler_MissingRequiredFields_ThrowsHttpErrorException(string filename, string inputKey, string outputKey)
    {
        // Arrange
        var command = new CreateTrackCommand(filename, inputKey, outputKey);
        var handler = new CreateTrackHandler(_loggerMock.Object, _tracksRepositoryMock.Object, _minioServiceMock.Object);

        // Act 
        var exception = await Assert.ThrowsAsync<HttpErrorException>(() => handler.Handle(command, CancellationToken.None));

        // Assert
        Assert.Equal(ExceptionDictionary.MissingRequiredFields, exception.ErrorMessage);
        Assert.Equal(HttpStatusCode.BadRequest, exception.HttpStatusCode);
    }

    [Fact]
    public async Task CreateTrackHandler_FileNotFoundInMinio_ThrowsHttpErrorException()
    {
        // Arrange
        _minioServiceMock
            .Setup(m => m.ObjectExistsAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(false);

        var command = new CreateTrackCommand(_defaultFileName, _defaultInputKey, _defaultOutputKey);
        var handler = new CreateTrackHandler(_loggerMock.Object, _tracksRepositoryMock.Object, _minioServiceMock.Object);

        // Act 
        var exception = await Assert.ThrowsAsync<HttpErrorException>(() => handler.Handle(command, CancellationToken.None));

        // Assert
        Assert.Equal(ExceptionDictionary.FileNotFoundInMinio, exception.ErrorMessage);
        Assert.Equal(HttpStatusCode.NotFound, exception.HttpStatusCode);
    }

    [Fact]
    public async Task CreateTrackHandler_NullTrackCreationFailed_ThrowsHttpErrorException()
    {
        // Arrange
        _tracksRepositoryMock
            .Setup(t => t.Create(It.IsAny<TrackEntity>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new ArgumentNullException());

        var command = new CreateTrackCommand(_defaultFileName, _defaultInputKey, _defaultOutputKey);
        var handler = new CreateTrackHandler(_loggerMock.Object, _tracksRepositoryMock.Object, _minioServiceMock.Object);

        // Act 
        var exception = await Assert.ThrowsAsync<HttpErrorException>(() => handler.Handle(command, CancellationToken.None));

        // Assert
        Assert.Equal(ExceptionDictionary.NullTrackCreationFailed, exception.ErrorMessage);
        Assert.Equal(HttpStatusCode.BadRequest, exception.HttpStatusCode);
    }

    [Fact]
    public async Task CreateTrackHandler_TrackCreationFailed_ThrowsHttpErrorException()
    {
        // Arrange
        _tracksRepositoryMock
            .Setup(t => t.Create(It.IsAny<TrackEntity>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new Exception());

        var command = new CreateTrackCommand(_defaultFileName, _defaultInputKey, _defaultOutputKey);
        var handler = new CreateTrackHandler(_loggerMock.Object, _tracksRepositoryMock.Object, _minioServiceMock.Object);

        // Act 
        var exception = await Assert.ThrowsAsync<HttpErrorException>(() => handler.Handle(command, CancellationToken.None));

        // Assert
        Assert.Equal(ExceptionDictionary.TrackCreationFailed, exception.ErrorMessage);
        Assert.Equal(HttpStatusCode.InternalServerError, exception.HttpStatusCode);
    }
}
