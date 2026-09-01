using AudioProcessing.Application.Jobs.GetJobStatus;
using AudioProcessing.Domain.Entities.Job;
using AudioProcessing.Domain.Exceptions;
using AudioProcessing.Infrastructure.Database.Repositories.Interfaces;
using Microsoft.Extensions.Logging;
using Moq;
using System.Net;

namespace UnitTests.Application.Jobs;

public class GetJobStatusHandlerTests
{
    private readonly Mock<ILogger<GetJobStatusHandler>> _loggerMock = new();
    private readonly Mock<IJobsRepository> _jobsRepositoryMock = new();
    private JobEntity DefaultJobEntity { get; set; }

    public GetJobStatusHandlerTests()
    {
        var randomMinioTrackGuid = Guid.NewGuid();
        DefaultJobEntity = new JobEntity
        {
            JobId = Guid.NewGuid(),
            Status = AudioProcessing.Domain.Enums.JobStatus.Queued,
            CreatedAt = DateTime.UtcNow,
            StartedAt = DateTime.UtcNow,
            FinishedAt = null,
            InputKey = $"input/{randomMinioTrackGuid}.mp3",
            OutputKey = $"output/{randomMinioTrackGuid}.mp3"
        };

        _jobsRepositoryMock
            .Setup(j => j.Read(It.IsAny<Guid>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(DefaultJobEntity);
    }

    [Fact]
    public async Task GetJobStatusHandler_JobFound_Success()
    {
        // Arrange
        var query = new GetJobStatusQuery(DefaultJobEntity.JobId);
        var handler = new GetJobStatusHandler(_loggerMock.Object, _jobsRepositoryMock.Object);

        // Act
        var response = await handler.Handle(query, CancellationToken.None);

        // Assert
        Assert.Equal(DefaultJobEntity.JobId, response.JobId);
        Assert.Equal(DefaultJobEntity.Status.ToString(), response.Status);
        Assert.Equal(DefaultJobEntity.InputKey, response.InputKey);
        Assert.Equal(DefaultJobEntity.OutputKey, response.OutputKey);
    }

    [Fact]
    public async Task GetJobStatusHandler_JobNotFound_ThrowsHttpErrorException()
    {
        // Arrange
        _jobsRepositoryMock
            .Setup(j => j.Read(It.IsAny<Guid>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((JobEntity?)null);

        var query = new GetJobStatusQuery(Guid.NewGuid());
        var handler = new GetJobStatusHandler(_loggerMock.Object, _jobsRepositoryMock.Object);

        // Act 
        var exception = await Assert.ThrowsAsync<HttpErrorException>(() => handler.Handle(query, CancellationToken.None));

        // Assert
        Assert.Equal(ExceptionDictionary.JobNotFound, exception.ErrorMessage);
        Assert.Equal(HttpStatusCode.NotFound, exception.HttpStatusCode);
    }

    [Fact]
    public async Task GetJobStatusHandler_JobGetInfoFailed_ThrowsHttpErrorException()
    {
        // Arrange
        _jobsRepositoryMock
            .Setup(j => j.Read(It.IsAny<Guid>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new Exception());

        var query = new GetJobStatusQuery(Guid.NewGuid());
        var handler = new GetJobStatusHandler(_loggerMock.Object, _jobsRepositoryMock.Object);

        // Act
        var exception = await Assert.ThrowsAsync<HttpErrorException>(() => handler.Handle(query, CancellationToken.None));

        // Assert
        Assert.Equal(ExceptionDictionary.JobGetInfoFailed, exception.ErrorMessage);
        Assert.Equal(HttpStatusCode.InternalServerError, exception.HttpStatusCode);
    }
}
