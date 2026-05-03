using System.Net;

namespace AudioProcessing.Domain.Exceptions;

public class HttpErrorException(string ErrorMessage, HttpStatusCode HttpStatusCode) : Exception
{
    public string ErrorMessage { get; set; } = ErrorMessage;
    public HttpStatusCode HttpStatusCode { get; set; } = HttpStatusCode;
}