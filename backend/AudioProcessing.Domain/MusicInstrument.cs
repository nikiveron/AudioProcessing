using System.Runtime.Serialization;

namespace AudioProcessing.Domain;

public enum MusicInstrument
{
    [EnumMember(Value = "Пианино")]
    Piano,
    [EnumMember(Value = "Бас-гитара")]
    Bass,
    [EnumMember(Value = "Электрогитара")]
    ElectroGuitar,
    [EnumMember(Value = "Акустическая гитара")]
    AcousticGuitar,
    [EnumMember(Value = "Вокал женский")]
    VocalFemale,
    [EnumMember(Value = "Вокал мужской")]
    VocalMale,
    [EnumMember(Value = "Бочка")]
    Kick,
    [EnumMember(Value = "Малый барабан")]
    Snare,
    [EnumMember(Value = "Том-том")]
    Tom,
    [EnumMember(Value = "Альт том")]
    AltTom,
    [EnumMember(Value = "Тарелки")]
    Overhead
}
