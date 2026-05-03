INSTRUMENTS = {
    "keys": {
        "module_path": "app.models.keys",
        "processor_fn": "process_audio_file",
        "description": "U-Net модель для обработки клавиш"
    },
    "bass": {
        "module_path": "app.models.bass",
        "processor_fn": "process_audio_file",
        "description": "U-Net модель для обработки бас-гитары"
    },
    # Шаблон для добавления нового инструмента:
    # "piano": {
    #     "module_path": "app.models.piano",
    #     "processor_fn": "process_audio_file",
    #     "description": "U-Net модель для обработки пианино"
    # },
}


def get_available_instruments():
    """Возвращает список доступных инструментов."""
    return list(INSTRUMENTS.keys())


def get_instrument_info(instrument_id: str):
    """Получить информацию об инструменте."""
    if instrument_id not in INSTRUMENTS:
        raise ValueError(f"Unknown instrument: {instrument_id}. Available: {get_available_instruments()}")
    return INSTRUMENTS[instrument_id]
