"""
Менеджер моделей - динамическая загрузка и кэширование обработчиков.
"""
from importlib import import_module
from .model_registry import get_instrument_info, get_available_instruments
import io


class ModelManager:
    """
    Менеджер моделей с кэшированием.
    Загружает обработчики по требованию и держит их в памяти.
    """
    
    def __init__(self):
        self._processors = {}  # Кэш загруженных обработчиков
        self._models = {}      # Кэш загруженных моделей
    
    def get_processor(self, instrument_id: str):
        """
        Получить процессор для инструмента.
        
        Args:
            instrument_id: ID инструмента (например, "keys", "gru")
            
        Returns:
            Функция process_audio_file для инструмента
            
        Raises:
            ValueError: Если инструмент не найден
        """
        if instrument_id in self._processors:
            return self._processors[instrument_id]
        
        # Загружаем модуль
        info = get_instrument_info(instrument_id)
        module_path = info["module_path"]
        processor_fn = info["processor_fn"]
        
        try:
            module = import_module(module_path)
            processor = getattr(module, processor_fn)
            
            # Кэшируем
            self._processors[instrument_id] = processor
            
            print(f"[Manager] Загружен процессор для '{instrument_id}': {module_path}.{processor_fn}")
            
            return processor
        except (ImportError, AttributeError) as e:
            raise ValueError(
                f"Не удалось загрузить процессор '{instrument_id}': {e}\n"
                f"Module: {module_path}, Function: {processor_fn}"
            )
    
    def process_audio(self, instrument_id: str, input_bytes: bytes, output_format: str = "WAV") -> io.BytesIO:
        """
        Обработать аудиофайл с выбранным инструментом.
        
        Args:
            instrument_id: ID инструмента
            input_bytes: Содержимое аудиофайла
            output_format: Формат выходного файла
            
        Returns:
            io.BytesIO: Буфер с обработанным аудио
        """
        processor = self.get_processor(instrument_id)
        return processor(input_bytes, output_format=output_format)
    
    def get_available_instruments(self):
        """Получить список доступных инструментов."""
        return get_available_instruments()
    
    def __repr__(self):
        instruments = self.get_available_instruments()
        cached = list(self._processors.keys())
        return (
            f"ModelManager(\n"
            f"  available: {instruments}\n"
            f"  cached: {cached}\n"
            f")"
        )


# Глобальный экземпляр менеджера
_global_manager = ModelManager()


def get_model_manager():
    """Получить глобальный экземпляр менеджера моделей."""
    return _global_manager
