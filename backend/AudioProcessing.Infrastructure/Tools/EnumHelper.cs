namespace AudioProcessing.Infrastructure.Tools;

public class EnumHelper
{
    public static Dictionary<Enum, string> GetEnumDictionary<T>() where T : Enum
    {
        var type = typeof(T);
        var values = Enum.GetValues(type).Cast<Enum>();
        var dict = new Dictionary<Enum, string>();
        foreach (var value in values)
        {
            var memberInfo = type.GetMember(value.ToString()).FirstOrDefault();
            var enumMemberAttribute = memberInfo?.GetCustomAttributes(typeof(System.Runtime.Serialization.EnumMemberAttribute), false)
                .FirstOrDefault() as System.Runtime.Serialization.EnumMemberAttribute;
            var stringValue = enumMemberAttribute != null ? enumMemberAttribute.Value : value.ToString();
            dict.Add(value, stringValue);
        }
        return dict;
    }
}
