"""
Импорт архитектуры модели из основного файла.
Это позволяет использовать одну основную реализацию для всех инструментов.
"""
from ..model_unet_improved import ImprovedUNetSeparator

__all__ = ["ImprovedUNetSeparator"]
