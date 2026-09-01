namespace AudioProcessing.Domain.Exceptions;

public static class ExceptionDictionary
{
    #region Common

    public static string KafkaProducerError => "Ошибка! Не удалось передать сообщение о новой задаче";

    #endregion

    #region Files

    public static string ObjectKeyRequired => "Ошибка! ObjectKey обязательный параметр";
    public static string FileNotFound => "Ошибка! Файл не был найден";
    public static string FileIsEmpty => "Ошибка! Не удалось загрузить файл или файл отсутствует";
    public static string FileUploadToMinioFailed => "Ошибка! Не удалось загрузить файл в хранилище";

    #endregion

    #region Jobs

    public static string JobNotFound => "Ошибка! Задача не найдена";
    public static string JobGetInfoFailed => "Ошибка! Не удалось получить статус задачи";
    public static string JobUpdateFailed => "Ошибка! Не удалось обновить задачу";

    #endregion

    #region Process

    public static string UnavaliableInstrument => "Ошибка! Передано некорректное название инструмента. Попробуйте другой инструмент";
    public static string TrackNotFound => "Ошибка! Трек не был найден";
    public static string NullJobCreationFailed => "Ошибка! Не удалось создать пустую задачу";
    public static string JobCreationFailed => "Ошибка! Не удалось создать задачу";

    #endregion

    #region Tracks

    public static string MissingRequiredFields => "Ошибка! Filename, OutputKey и InputKey обязательные параметры";
    public static string FileNotFoundInMinio => "Ошибка! Файл не был найден в хранилище Minio";
    public static string NullTrackCreationFailed => "Ошибка! Не удалось создать пустой трек";
    public static string TrackCreationFailed => "Ошибка! Не удалось создать трек";
    public static string TrackNotFoundInDatabase => "Ошибка! Информация о треке не была найдена в базе данных";

    #endregion
}
