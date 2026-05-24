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
    "ag": {
        "module_path": "app.models.ag",
        "processor_fn": "process_audio_file",
        "description": "U-Net модель для обработки акустической гитары"
    },
    "eg": {
        "module_path": "app.models.eg",
        "processor_fn": "process_audio_file",
        "description": "U-Net модель для обработки электрогитары"
    },
}


def get_available_instruments():
    return list(INSTRUMENTS.keys())


def get_instrument_info(instrument_id: str):
    if instrument_id not in INSTRUMENTS:
        raise ValueError(f"Unknown instrument: {instrument_id}. Available: {get_available_instruments()}")
    return INSTRUMENTS[instrument_id]
