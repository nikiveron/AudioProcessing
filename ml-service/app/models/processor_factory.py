from typing import Dict, Type
from app.models.strategies.base import BaseProcessingStrategy
from app.models.strategies.ag_strategy import AGProcessingStrategy
from app.models.strategies.eg_strategy import EGProcessingStrategy
from app.models.strategies.bass_strategy import BassProcessingStrategy
from app.models.strategies.keys_strategy import KeysProcessingStrategy


class ProcessingStrategyFactory:
    _strategy_classes: Dict[str, Type[BaseProcessingStrategy]] = {
        "ag": AGProcessingStrategy,
        "eg": EGProcessingStrategy,
        "bass": BassProcessingStrategy,
        "keys": KeysProcessingStrategy,
    }
    
    def __init__(self):
        self._strategies: Dict[str, BaseProcessingStrategy] = {}
    
    def get_strategy(self, instrument_id: str) -> BaseProcessingStrategy:
        if instrument_id in self._strategies:
            return self._strategies[instrument_id]
        
        if instrument_id not in self._strategy_classes:
            available = ", ".join(self._strategy_classes.keys())
            raise ValueError(
                f"Неизвестный инструмент: {instrument_id}. Доступные: {available}"
            )
        
        strategy_class = self._strategy_classes[instrument_id]
        strategy = strategy_class()
        self._strategies[instrument_id] = strategy
        
        print(f"[Factory] Создана стратегия для '{instrument_id}': {strategy_class.__name__}")
        
        return strategy
    
    def process_audio(self, instrument_id: str, input_bytes: bytes, 
                     output_format: str = "WAV"):
        strategy = self.get_strategy(instrument_id)
        return strategy.process_audio_file(input_bytes, output_format=output_format)
    
    def get_available_instruments(self):
        return list(self._strategy_classes.keys())


_global_factory = ProcessingStrategyFactory()


def get_strategy_factory() -> ProcessingStrategyFactory:
    """Получает глобальный экземпляр фабрики."""
    return _global_factory
