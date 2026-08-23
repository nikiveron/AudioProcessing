
using AudioProcessing.Application.Files.DownloadFile;
using AudioProcessing.Infrastructure.Storage;
using Microsoft.Extensions.Logging;
using Moq;

namespace UnitTests.Application.Files;

public class DownloadFileHandlerTests
{
    private readonly Mock<ILogger<DownloadFileHandler>> _loggerMock = new();
    private readonly Mock<MinioService> _miniServiceMock = new();
    private readonly string _defaultPathToFile = "path-to-file";
    private readonly string _defaultFileName = "file-name";
    private readonly string _defaultExtension = ".wav";
    private string DefaultObjectKey => _defaultPathToFile + "/" + _defaultFileName + _defaultExtension;

    [Fact]
    public async Task DownloadFileHandler_ObjectKeyExists_Success()
    {
        // Arrange
        var query = new DownloadFileQuery(DefaultObjectKey);
        var handler = new DownloadFileHandler(_loggerMock.Object, _miniServiceMock.Object);

        // Act
        var response = await handler.Handle(query, CancellationToken.None);

        // Assert
        Assert.Equal(_defaultFileName, response.Filename);

    }
}
