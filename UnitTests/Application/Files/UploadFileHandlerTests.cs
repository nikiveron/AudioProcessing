using AudioProcessing.Application.Files.UploadFile;
using AudioProcessing.Domain.Exceptions;
using AudioProcessing.Infrastructure.Storage;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;
using Moq;
using System.Net;

namespace UnitTests.Application.Files;

public class UploadFileHandlerTests
{
    private readonly Mock<ILogger<UploadFileHandler>> _loggerMock = new();
    private readonly Mock<IMinioService> _minioServiceMock = new();
    private readonly Mock<IFormFile> _formFileMock = new();
    private readonly string _defaultFileName = "file-name";
    private readonly string _defaultExtension = ".wav";
    private readonly string _defaultContentType = "audio/wav";

    public UploadFileHandlerTests()
    {
        _formFileMock.Setup(f => f.FileName).Returns(_defaultFileName + _defaultExtension);
        _formFileMock.Setup(f => f.ContentType).Returns(_defaultContentType);
        _formFileMock.Setup(f => f.Length).Returns(1024);
    }

    [Fact]
    public async Task UploadFileHandler_FileUploaded_Success()
    {
        // Arrange
        var command = new UploadFileCommand(_formFileMock.Object);
        var handler = new UploadFileHandler(_loggerMock.Object, _minioServiceMock.Object);

        // Act
        var response = await handler.Handle(command, CancellationToken.None);

        // Assert
        Assert.Contains(_defaultFileName + _defaultExtension, response.InputKey);
        Assert.Contains("input/", response.InputKey);
        Assert.Contains(_defaultFileName + _defaultExtension, response.OutputKey);
        Assert.Contains("output/", response.OutputKey);
    }

    [Fact]
    public async Task UploadFileHandler_FileIsEmpty_ThrowsHttpErrorException()
    {
        // Arrange
        _formFileMock.Setup(f => f.Length).Returns(0);

        var command = new UploadFileCommand(_formFileMock.Object);
        var handler = new UploadFileHandler(_loggerMock.Object, _minioServiceMock.Object);

        // Act 
        var exception = await Assert.ThrowsAsync<HttpErrorException>(() => handler.Handle(command, CancellationToken.None));

        // Assert
        Assert.Equal(ExceptionDictionary.FileIsEmpty, exception.ErrorMessage);
        Assert.Equal(HttpStatusCode.BadRequest, exception.HttpStatusCode);
    }

    [Fact]
    public async Task UploadFileHandler_FileUploadToMinioFailed_ThrowsHttpErrorException()
    {
        // Arrange
        _minioServiceMock
            .Setup(m => m.UploadObjectAsync(It.IsAny<string>(), It.IsAny<Stream>(), It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new Exception());

        var command = new UploadFileCommand(_formFileMock.Object);
        var handler = new UploadFileHandler(_loggerMock.Object, _minioServiceMock.Object);

        // Act 
        var exception = await Assert.ThrowsAsync<HttpErrorException>(() => handler.Handle(command, CancellationToken.None));

        // Assert
        Assert.Equal(ExceptionDictionary.FileUploadToMinioFailed, exception.ErrorMessage);
        Assert.Equal(HttpStatusCode.InternalServerError, exception.HttpStatusCode);
    }
}
