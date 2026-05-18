using AudioProcessing.Domain.Enums;
using AudioProcessing.Infrastructure.Tools;
using Microsoft.AspNetCore.Mvc;

namespace AudioProcessing.API.Controllers;

/// <summary>
/// Контроллер для получения справочных данных, таких как список музыкальных инструментов и жанров. 
/// Эти данные могут использоваться на клиентской стороне для отображения пользователю доступных опций при выборе параметров обработки аудио.
/// </summary>
[ApiController]
[Route("api/common")]
public class CommonController : ControllerBase
{
    /// <summary>
    /// Получает словарь доступных музыкальных инструментов с соответствующими значениями.
    /// </summary>
    /// <remarks>Этот endpoint обычно используется для заполнения списков выбора или предоставления клиентам набора
    /// поддерживаемых музыкальных инструментов. Формат ответа подходит для использования в пользовательских интерфейсах или экранах конфигурации.</remarks>
    /// <returns>Объект <see cref="IActionResult"/>, содержащий словарь, который сопоставляет каждое имя музыкального инструмента с его значением.</returns>
    [HttpGet("instruments")]
    public IActionResult GetInstruments()
    {
        return Ok(EnumHelper.GetEnumDictionary<MusicInstrument>());
    }

    /// <summary>
    /// Получает словарь доступных музыкальных жанров с соответствующими целыми числовыми значениями.
    /// </summary>
    /// <remarks>Этот endpoint можно использовать для заполнения элементов пользовательского интерфейса, таких как раскрывающиеся списки,
    /// доступными музыкальными жанрами. Ответ включает все определённые значения в перечислении <see cref="MusicGenre"/>.</remarks>
    /// <returns>Объект <see cref="OkObjectResult"/>, содержащий словарь, где ключи — целые значения перечисления <see cref="MusicGenre"/>,
    /// а значения — их строковые представления.</returns>
    [HttpGet("genres")]
    public IActionResult GetGenres()
    {
        return Ok(EnumHelper.GetEnumDictionary<MusicGenre>());
    }
}