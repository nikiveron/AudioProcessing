using AudioProcessing.Application.Jobs.UpdateJob;
using AudioProcessing.Domain.Entities.Job;
using AudioProcessing.Domain.Enums;
using AudioProcessing.Domain.Exceptions;
using AudioProcessing.Infrastructure.Database.Repositories.Interfaces;
using Microsoft.Extensions.Logging;
using Moq;
using System.Net;

namespace UnitTests.Application.Jobs;

public class UpdateJobHandlerTests
{
    private readonly Mock<ILogger<UpdateJobHandler>> _loggerMock = new();
    private readonly Mock<IJobsRepository> _jobsRepositoryMock = new();
    private JobEntity ExistingJobEntity { get; init; }

    public UpdateJobHandlerTests()
    {
        var randomMinioTrackGuid = Guid.NewGuid();
        ExistingJobEntity = new JobEntity
        {
            JobId = Guid.NewGuid(),
            Status = JobStatus.Queued,
            CreatedAt = DateTime.UtcNow,
            StartedAt = DateTime.UtcNow,
            FinishedAt = null,
            InputKey = $"input/{randomMinioTrackGuid}.mp3",
            OutputKey = $"output/{randomMinioTrackGuid}.mp3"
        };

        _jobsRepositoryMock
            .Setup(j => j.Read(It.IsAny<Guid>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(new JobEntity()
            {
                JobId = ExistingJobEntity.JobId,
                Status = ExistingJobEntity.Status,
                CreatedAt = ExistingJobEntity.CreatedAt,
                StartedAt = ExistingJobEntity.StartedAt,
                FinishedAt = ExistingJobEntity.FinishedAt,
                InputKey = ExistingJobEntity.InputKey,
                OutputKey = ExistingJobEntity.OutputKey
            });
    }

    [Fact]
    public async Task UpdateJobHandler_JobUpdated_Success()
    {
        // Arrange
        var testJobEntity = new JobEntity
        {
            JobId = ExistingJobEntity.JobId,
            Status = JobStatus.Success,
            CreatedAt = ExistingJobEntity.CreatedAt,
            StartedAt = ExistingJobEntity.StartedAt,
            FinishedAt = ExistingJobEntity.FinishedAt,
            InputKey = ExistingJobEntity.InputKey,
            OutputKey = $"output/{Guid.NewGuid()}.mp3"
        };

        var command = new UpdateJobCommand(
            testJobEntity.JobId,
            testJobEntity.Status,
            testJobEntity.OutputKey,
            testJobEntity.StartedAt,
            testJobEntity.FinishedAt
        );
        var handler = new UpdateJobHandler(_loggerMock.Object, _jobsRepositoryMock.Object);

        // Act
        var response = await handler.Handle(command, CancellationToken.None);

        // Assert
        Assert.Equal(testJobEntity.Status.ToString(), response.Status);
        Assert.Equal(testJobEntity.OutputKey, response.OutputKey);
    }

    [Fact]
    public async Task UpdateJobHandler_JobNotFound_ThrowsHttpErrorException()
    {
        // Arrange
        _jobsRepositoryMock
            .Setup(j => j.Read(It.IsAny<Guid>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((JobEntity?)null);

        var command = new UpdateJobCommand(
            ExistingJobEntity.JobId,
            ExistingJobEntity.Status,
            ExistingJobEntity.OutputKey,
            ExistingJobEntity.StartedAt,
            ExistingJobEntity.FinishedAt
        );
        var handler = new UpdateJobHandler(_loggerMock.Object, _jobsRepositoryMock.Object);

        // Act
        var exception = await Assert.ThrowsAsync<HttpErrorException>(() => handler.Handle(command, CancellationToken.None));

        // Assert
        Assert.Equal(ExceptionDictionary.JobNotFound, exception.ErrorMessage);
        Assert.Equal(HttpStatusCode.NotFound, exception.HttpStatusCode);
    }

    [Fact]
    public async Task UpdateJobHandler_JobUpdateFailed_ThrowsHttpErrorException()
    {
        // Arrange
        _jobsRepositoryMock
            .Setup(j => j.Read(It.IsAny<Guid>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new Exception());

        var command = new UpdateJobCommand(
            ExistingJobEntity.JobId,
            ExistingJobEntity.Status,
            ExistingJobEntity.OutputKey,
            ExistingJobEntity.StartedAt,
            ExistingJobEntity.FinishedAt
        );
        var handler = new UpdateJobHandler(_loggerMock.Object, _jobsRepositoryMock.Object);

        // Act
        var exception = await Assert.ThrowsAsync<HttpErrorException>(() => handler.Handle(command, CancellationToken.None));

        // Assert
        Assert.Equal(ExceptionDictionary.JobUpdateFailed, exception.ErrorMessage);
        Assert.Equal(HttpStatusCode.InternalServerError, exception.HttpStatusCode);
    }
}
