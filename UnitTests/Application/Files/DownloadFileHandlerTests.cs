using AudioProcessing.Application.Files.DownloadFile;
using AudioProcessing.Domain.Exceptions;
using AudioProcessing.Infrastructure.Storage;
using Microsoft.Extensions.Logging;
using Moq;
using System.Net;

namespace UnitTests.Application.Files;

public class DownloadFileHandlerTests
{
    private readonly Mock<ILogger<DownloadFileHandler>> _loggerMock = new();
    private readonly Mock<IMinioService> _minioServiceMock = new();
    private readonly string _defaultPathToFile = "path-to-file";
    private readonly string _defaultFileName = "file-name";
    private readonly string _defaultExtension = ".wav";
    private readonly string _defaultContentType = "audio/wav";
    private string DefaultObjectKey => Path.Combine(_defaultPathToFile, _defaultFileName + _defaultExtension);

    [Fact]
    public async Task DownloadFileHandler_ObjectKeyExists_WavFile_Success()
    {
        // Arrange
        var query = new DownloadFileQuery(DefaultObjectKey);
        var handler = new DownloadFileHandler(_loggerMock.Object, _minioServiceMock.Object);

        // Act
        var response = await handler.Handle(query, CancellationToken.None);

        // Assert
        Assert.Equal(_defaultFileName + _defaultExtension, response.Filename);
        Assert.Equal(_defaultContentType, response.ContentType);
    }

    [Fact]
    public async Task DownloadFileHandler_ObjectKeyExists_Mp3File_Success()
    {
        // Arrange
        var testMp3Extension = ".mp3";
        var filePath = Path.Combine(_defaultPathToFile, _defaultFileName + testMp3Extension);
        var query = new DownloadFileQuery(filePath);
        var handler = new DownloadFileHandler(_loggerMock.Object, _minioServiceMock.Object);

        // Act
        var response = await handler.Handle(query, CancellationToken.None);

        // Assert
        Assert.Equal(_defaultFileName + testMp3Extension, response.Filename);
        Assert.Equal("audio/mpeg", response.ContentType);
    }

    [Fact]
    public async Task DownloadFileHandler_ObjectKeyExists_OggFile_Success()
    {
        // Arrange
        var testOggExtension = ".ogg";
        var filePath = Path.Combine(_defaultPathToFile, _defaultFileName + testOggExtension);
        var query = new DownloadFileQuery(filePath);
        var handler = new DownloadFileHandler(_loggerMock.Object, _minioServiceMock.Object);

        // Act
        var response = await handler.Handle(query, CancellationToken.None);

        // Assert
        Assert.Equal(_defaultFileName + testOggExtension, response.Filename);
        Assert.Equal("application/octet-stream", response.ContentType);
    }

    [Fact]
    public async Task DownloadFileHandler_ObjectKeyIsNull_ThrowsHttpErrorException()
    {
        // Arrange
        var query = new DownloadFileQuery(string.Empty);
        var handler = new DownloadFileHandler(_loggerMock.Object, _minioServiceMock.Object);

        // Act 
        var exception = await Assert.ThrowsAsync<HttpErrorException>(() => handler.Handle(query, CancellationToken.None));

        // Assert
        Assert.Equal(ExceptionDictionary.ObjectKeyRequired, exception.ErrorMessage);
        Assert.Equal(HttpStatusCode.BadRequest, exception.HttpStatusCode);
    }

    [Fact]
    public async Task DownloadFileHandler_FileNotFound_ThrowsHttpErrorException()
    {
        // Arrange
        _minioServiceMock
            .Setup(s => s.GetObjectStreamAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new Exception());

        var query = new DownloadFileQuery(DefaultObjectKey);
        var handler = new DownloadFileHandler(_loggerMock.Object, _minioServiceMock.Object);

        // Act 
        var exception = await Assert.ThrowsAsync<HttpErrorException>(() => handler.Handle(query, CancellationToken.None));

        // Assert
        Assert.Equal(ExceptionDictionary.FileNotFound, exception.ErrorMessage);
        Assert.Equal(HttpStatusCode.NotFound, exception.HttpStatusCode);
    }
}
