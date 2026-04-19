using System.Runtime.Serialization;

namespace AudioProcessing.Domain;

public enum MusicGenre
{
    [EnumMember(Value = "Классика")]
    Classic,
    [EnumMember(Value = "Джаз")]
    Jazz,
    [EnumMember(Value = "Рок")]
    Rock
}
