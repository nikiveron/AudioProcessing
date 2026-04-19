using System.Runtime.Serialization;

namespace AudioProcessing.Domain;

public enum MusicInstrument
{
    [EnumMember(Value = "Гитара")]
    Guitar,
    [EnumMember(Value = "Пианино")] 
    Piano,
    [EnumMember(Value = "Вокал")]
    Vocal
}
