using AudioProcessing.Application.Process.StartProcess;
using AudioProcessing.Domain.Entities.Job;
using AudioProcessing.Domain.Entities.Track;
using AudioProcessing.Domain.Enums;
using AudioProcessing.Domain.Exceptions;
using AudioProcessing.Infrastructure.Database.Repositories.Interfaces;
using Confluent.Kafka;
using Microsoft.Extensions.Logging;
using Moq;
using System.Net;

namespace UnitTests.Application.Process;

public class StartProcessHandlerTests
{
    private readonly Mock<ILogger<StartProcessHandler>> _loggerMock = new();
    private readonly Mock<ITracksRepository> _tracksRepositoryMock = new();
    private readonly Mock<IJobsRepository> _jobsRepositoryMock = new();
    private readonly Mock<IProducer<Null, string>> _producerMock = new();
    private readonly string _defaultInstrument = MusicInstrument.AcousticGuitar.ToString();
    private readonly TrackEntity _defaultTrackEntity = new()
    {
        TrackId = Guid.NewGuid(),
        InputKey = "input/test.mp3",
        OutputKey = "output/test.mp3"
    };

    public StartProcessHandlerTests()
    {
        _tracksRepositoryMock
            .Setup(t => t.Read(It.IsAny<Guid>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((Guid id, CancellationToken ct) => _defaultTrackEntity);
    }

    [Fact]
    public async Task StartProcessHandler_ProcessStarted_Success()
    {
        // Arrange
        var command = new StartProcessCommand(Guid.NewGuid(), _defaultInstrument);
        var handler = new StartProcessHandler(_loggerMock.Object, _tracksRepositoryMock.Object, _jobsRepositoryMock.Object, _producerMock.Object);

        // Act
        var response = await handler.Handle(command, CancellationToken.None);

        // Assert
        Assert.NotEqual(Guid.Empty, response);
    }

    [Fact]
    public async Task StartProcessHandler_UnavaliableInstrument_ThrowsHttpErrorException()
    {
        // Arrange
        var command = new StartProcessCommand(Guid.NewGuid(), "any-invalid-instrument");
        var handler = new StartProcessHandler(_loggerMock.Object, _tracksRepositoryMock.Object, _jobsRepositoryMock.Object, _producerMock.Object);

        // Act
        var exception = await Assert.ThrowsAsync<HttpErrorException>(() => handler.Handle(command, CancellationToken.None));

        // Assert
        Assert.Equal(ExceptionDictionary.UnavaliableInstrument, exception.ErrorMessage);
        Assert.Equal(HttpStatusCode.BadRequest, exception.HttpStatusCode);
    }

    [Fact]
    public async Task StartProcessHandler_TrackNotFound_ThrowsHttpErrorException()
    {
        // Arrange
        _tracksRepositoryMock
            .Setup(t => t.Read(It.IsAny<Guid>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((Guid id, CancellationToken ct) => null);

        var command = new StartProcessCommand(Guid.NewGuid(), _defaultInstrument);
        var handler = new StartProcessHandler(_loggerMock.Object, _tracksRepositoryMock.Object, _jobsRepositoryMock.Object, _producerMock.Object);

        // Act
        var exception = await Assert.ThrowsAsync<HttpErrorException>(() => handler.Handle(command, CancellationToken.None));

        // Assert
        Assert.Equal(ExceptionDictionary.TrackNotFound, exception.ErrorMessage);
        Assert.Equal(HttpStatusCode.NotFound, exception.HttpStatusCode);
    }

    [Fact]
    public async Task StartProcessHandler_NullJobCreationFailed_ThrowsHttpErrorException()
    {
        // Arrange
        _jobsRepositoryMock
            .Setup(t => t.Create(It.IsAny<JobEntity>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new ArgumentNullException());

        var command = new StartProcessCommand(Guid.NewGuid(), _defaultInstrument);
        var handler = new StartProcessHandler(_loggerMock.Object, _tracksRepositoryMock.Object, _jobsRepositoryMock.Object, _producerMock.Object);

        // Act
        var exception = await Assert.ThrowsAsync<HttpErrorException>(() => handler.Handle(command, CancellationToken.None));

        // Assert
        Assert.Equal(ExceptionDictionary.NullJobCreationFailed, exception.ErrorMessage);
        Assert.Equal(HttpStatusCode.BadRequest, exception.HttpStatusCode);
    }

    [Fact]
    public async Task StartProcessHandler_JobCreationFailed_ThrowsHttpErrorException()
    {
        // Arrange
        _jobsRepositoryMock
            .Setup(t => t.Create(It.IsAny<JobEntity>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new Exception());

        var command = new StartProcessCommand(Guid.NewGuid(), _defaultInstrument);
        var handler = new StartProcessHandler(_loggerMock.Object, _tracksRepositoryMock.Object, _jobsRepositoryMock.Object, _producerMock.Object);

        // Act
        var exception = await Assert.ThrowsAsync<HttpErrorException>(() => handler.Handle(command, CancellationToken.None));

        // Assert
        Assert.Equal(ExceptionDictionary.JobCreationFailed, exception.ErrorMessage);
        Assert.Equal(HttpStatusCode.InternalServerError, exception.HttpStatusCode);
    }
    [Theory]
    [InlineData(typeof(ProduceException<Null, string>))]
    [InlineData(typeof(KafkaException))]
    [InlineData(typeof(Exception))]
    public async Task StartProcessHandler_KafkaProducerError_ThrowsHttpErrorException(
    Type exceptionType)
    {
        // Arrange
        var producerException = CreateException(exceptionType);
        _producerMock
            .Setup(p => p.ProduceAsync(It.IsAny<string>(), It.IsAny<Message<Null, string>>(), CancellationToken.None))
            .ThrowsAsync(producerException);

        var command = new StartProcessCommand(Guid.NewGuid(), _defaultInstrument);
        var handler = new StartProcessHandler(_loggerMock.Object, _tracksRepositoryMock.Object, _jobsRepositoryMock.Object, _producerMock.Object);

        // Act
        var exception = await Assert.ThrowsAsync<HttpErrorException>(() => handler.Handle(command, CancellationToken.None));

        // Assert
        Assert.Equal(ExceptionDictionary.KafkaProducerError, exception.ErrorMessage);
        Assert.Equal(HttpStatusCode.InternalServerError, exception.HttpStatusCode);
    }

    #region Helpers 

    private static Exception CreateException(Type exceptionType)
    {
        if (exceptionType == typeof(Exception))
            return new Exception("Test exception");

        if (exceptionType == typeof(KafkaException))
            return new KafkaException(
                new Error(ErrorCode.Local_Fail));

        if (exceptionType == typeof(ProduceException<Null, string>))
            return new ProduceException<Null, string>(
                new Error(ErrorCode.Local_Fail),
                new DeliveryResult<Null, string>());

        throw new ArgumentException(
            $"Unsupported exception type: {exceptionType}");
    }

    #endregion
}
