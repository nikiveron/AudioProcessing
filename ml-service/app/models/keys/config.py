import os

# Путь к весам модели - основной файл с весами клавиш
MODEL_PATH = os.getenv("KEYS_MODEL_PATH", "model_weights_keys_improved_unet.pth")

# Параметры обработки звука
SAMPLE_RATE = 48000

# Параметры модели (совпадают с основной моделью)
MODEL_CONFIG = {
    "input_size": 1025,
    "base_channels": 32,
    "dropout_rate": 0.1
}

# Параметры STFT
N_FFT = 2048
HOP = 512
WIN_LENGTH = 2048
WINDOW = "hann"

# Параметры обработки overlap-add
CHUNK_SIZE = 15  # секунды
OVERLAP_RATIO = 0.3  # 30% перекрытия

# Устройство
DEVICE = os.getenv("DEVICE", "cuda")
