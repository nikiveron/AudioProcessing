import os
from pathlib import Path
import torch

# Путь к весам модели - основной файл с весами клавиш
MODEL_PATH = Path(os.getenv("BASS_MODEL_PATH", "model_weights_bass_improved_unet.pth"))

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
_device_str = os.getenv("DEVICE", "cuda")
if _device_str == "mps":
    DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
elif _device_str == "cuda":
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
else:
    DEVICE = torch.device("cpu")
