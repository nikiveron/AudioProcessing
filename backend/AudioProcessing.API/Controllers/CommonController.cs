using AudioProcessing.Domain;
using AudioProcessing.Infrastructure.Storage;
using AudioProcessing.Infrastructure.Tools;
using Microsoft.AspNetCore.Mvc;

namespace AudioProcessing.API.Controllers;

[ApiController]
[Route("api/common")]
public class CommonController : ControllerBase
{
    [HttpGet("instruments")]
    public IActionResult GetInstruments()
    {
        return Ok(EnumHelper.GetEnumDictionary<MusicInstrument>());
    }

    [HttpGet("genres")]
    public IActionResult GetGenres()
    {
        return Ok(EnumHelper.GetEnumDictionary<MusicGenre>());
    }
}