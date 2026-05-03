using System.Runtime.Serialization;

namespace AudioProcessing.Infrastructure.Tools;

public class EnumHelper
{
    public static Dictionary<string, string> GetEnumDictionary<T>() where T : Enum
    {
        var type = typeof(T);
        var values = Enum.GetValues(type).Cast<Enum>();
        var dict = new Dictionary<string, string>();

        foreach (var value in values)
        {
            var memberInfo = type.GetMember(value.ToString()).FirstOrDefault();
            var stringValue = memberInfo?.GetCustomAttributes(typeof(EnumMemberAttribute), false)
                .FirstOrDefault() is EnumMemberAttribute enumMemberAttribute
                    ? enumMemberAttribute.Value
                    : value.ToString();

            dict.Add(value.ToString(), stringValue ?? value.ToString());
        }
        return dict;
    }
}
