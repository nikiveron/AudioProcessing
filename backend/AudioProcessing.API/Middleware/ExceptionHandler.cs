using AudioProcessing.Domain.Exceptions;
using Microsoft.AspNetCore.Diagnostics;
using System.Net;

namespace AudioProcessing.API.Middleware;

public class ExceptionHandler(ILogger<ExceptionHandler> logger) : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(HttpContext httpContext, Exception exception, CancellationToken cancellationToken)
    {
        List<ExceptionResponse> response = exception switch
        {
            HttpErrorException httpErrorException => PrepareHttpErrorException(httpErrorException, httpContext),
            _ => PrepareFormattedError(exception, httpContext, HttpStatusCode.BadRequest)
        };

        httpContext.Response.ContentType = "application/json";
        await httpContext.Response.WriteAsJsonAsync(response, cancellationToken);
        return true;
    }

    private List<ExceptionResponse> PrepareHttpErrorException(HttpErrorException exception, HttpContext httpContext)
    {
        var statusCode = (int)exception.HttpStatusCode;
        var errorMessage = $"Код ошибки {statusCode}. Ошибка: {exception.ErrorMessage}";
        logger.LogError(errorMessage);
        httpContext.Response.StatusCode = statusCode;
        return [new(statusCode.ToString(), exception.ErrorMessage)];
    }

    private List<ExceptionResponse> PrepareFormattedError(Exception exception, HttpContext httpContext, HttpStatusCode httpStatusCode)
    {
        logger.LogError("Произошла непредвиденная ошибка при обработке запроса. {stackTrace}", exception.StackTrace);
        var message = exception.InnerException !=null && !string.IsNullOrEmpty(exception.InnerException.Message) ? exception.InnerException.Message : exception.Message;
        httpContext.Response.StatusCode = (int)httpStatusCode;
        return [new(((int)httpStatusCode).ToString(), message)];
    }
}
