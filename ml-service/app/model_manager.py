from app.models.processor_factory import get_strategy_factory
import io


class ModelManager:
    def __init__(self):
        self._factory = get_strategy_factory()
    
    def process_audio(self, instrument_id: str, input_bytes: bytes, output_format: str = "WAV") -> io.BytesIO:
        """
        Обрабатывает аудио используя стратегию для инструмента.
        """
        return self._factory.process_audio(instrument_id, input_bytes, output_format=output_format)
    
    def get_available_instruments(self):
        return self._factory.get_available_instruments()
    
    def __repr__(self):
        instruments = self.get_available_instruments()
        return (
            f"ModelManager(\n"
            f"  available: {instruments}\n"
            f")"
        )


_global_manager = ModelManager()


def get_model_manager():
    return _global_manager
