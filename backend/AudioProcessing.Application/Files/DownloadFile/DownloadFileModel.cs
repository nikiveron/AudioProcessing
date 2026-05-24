// DownloadFileModel.cs
namespace AudioProcessing.Application.Files.DownloadFile;

public record DownloadFileModel(Stream Stream, string ContentType, string Filename);
