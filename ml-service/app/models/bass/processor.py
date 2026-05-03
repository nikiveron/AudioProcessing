"""
Процессор для обработки аудио бас-гитары с помощью улучшенной U-Net модели.
Использует overlap-add для плавных переходов между чанками.
Алгоритм аналогичен process_bass.py:
- Overlap-add обработка для плавных переходов
- Low-pass фильтр 5kHz для баса
- Компенсация громкости
"""
import io
import os
import torch
import librosa
import soundfile as sf
import numpy as np
from scipy import signal

from ..model_unet_improved import ImprovedUNetSeparator
from ..utils_unet import stft_spectrogram, stft_to_audio
from .config import (
    MODEL_PATH, SAMPLE_RATE, MODEL_CONFIG,
    DEVICE, CHUNK_SIZE, OVERLAP_RATIO
)

# Глобальная переменная для модели (загружаем один раз)
_model = None
_device = None


def load_model():
    """Загружает модель при первом вызове."""
    global _model, _device
    
    if _model is not None:
        return _model
    
    _device = torch.device(
        DEVICE if torch.cuda.is_available()
        else "mps" if torch.backends.mps.is_available()
        else "cpu"
    )
    
    _model = ImprovedUNetSeparator(**MODEL_CONFIG).to(_device)
    
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Модель не найдена: {MODEL_PATH}")
    
    _model.load_state_dict(torch.load(MODEL_PATH, map_location=_device))
    _model.eval()
    
    print(f"[Bass Model] Загружена модель из {MODEL_PATH}")
    print(f"  Устройство: {_device}")
    
    return _model


def process_audio_file(input_bytes: bytes, output_format: str = "WAV") -> io.BytesIO:
    """
    Обработать аудиофайл моделью с overlap-add для плавных переходов.
    
    Args:
        input_bytes: Содержимое аудиофайла в байтах
        output_format: Формат выходного файла (WAV, MP3 и т.д.)
        
    Returns:
        io.BytesIO: Буфер с обработанным аудио
    """
    model = load_model()
    device = _device
    
    # Загружаем аудио
    audio, sr = librosa.load(io.BytesIO(input_bytes), sr=SAMPLE_RATE)
    
    # Обработка целого файла или с overlap-add
    chunk_samples = int(CHUNK_SIZE * SAMPLE_RATE)
    
    if len(audio) < chunk_samples:
        # Маленький файл - обрабатываем целиком
        output_audio = _process_short_audio(model, device, audio)
    else:
        # Большой файл - используем overlap-add
        output_audio = _process_long_audio_overlap_add(model, device, audio)
    
    # Low-pass фильтр для удаления высокочастотных шумов (бас < 5kHz)
    nyquist = sr / 2
    cutoff = 5000  # 5 kHz для баса
    b, a = signal.butter(4, cutoff / nyquist, btype='low')
    output_audio = signal.filtfilt(b, a, output_audio)
    
    # Компенсация громкости (make-up gain)
    input_rms = np.sqrt(np.mean(audio ** 2))
    output_rms = np.sqrt(np.mean(output_audio ** 2))
    if output_rms > 1e-6:
        gain = input_rms / output_rms
        output_audio = output_audio * gain * 0.95
        print(f"  Компенсация громкости: gain={gain:.2f}")
    print(f"  RMS выхода: {np.sqrt(np.mean(output_audio ** 2)):.6f}")
    
    # Нормализуем выход
    max_val = np.max(np.abs(output_audio))
    if max_val > 1.0:
        output_audio = output_audio / max_val
    
    # Сохраняем в буфер
    output_buf = io.BytesIO()
    sf.write(output_buf, output_audio, sr, format=output_format)
    output_buf.seek(0)
    
    return output_buf


def _process_short_audio(model, device, audio):
    """Обработка короткого аудио целиком."""
    print("Обрабатываю аудио целиком...")
    input_rms = np.sqrt(np.mean(audio ** 2))
    print(f"  RMS оригинала: {input_rms:.6f}")
    
    magnitude_norm, phase = stft_spectrogram(audio, sr=SAMPLE_RATE)
    
    mag_tensor = torch.tensor(magnitude_norm).unsqueeze(0).unsqueeze(0).float().to(device)
    
    with torch.no_grad():
        output_mag = model(mag_tensor)
    
    output_mag = output_mag.squeeze(0).squeeze(0).cpu().numpy()
    output_mag = np.clip(output_mag, 0, 1)
    
    # Паддинг до 1025 бинов если нужно
    if output_mag.shape[0] < 1025:
        output_mag_padded = np.zeros((1025, output_mag.shape[1]), dtype=output_mag.dtype)
        output_mag_padded[:output_mag.shape[0], :] = output_mag
        output_mag = output_mag_padded
    
    if phase.shape[0] != output_mag.shape[0]:
        phase_padded = np.zeros((output_mag.shape[0], phase.shape[1]), dtype=phase.dtype)
        phase_padded[:phase.shape[0], :] = phase
        phase = phase_padded
    if phase.shape[1] != output_mag.shape[1]:
        phase = phase[:, :output_mag.shape[1]]
    
    return stft_to_audio(output_mag, phase, sr=SAMPLE_RATE)


def _process_long_audio_overlap_add(model, device, audio):
    """Обработка длинного аудио с overlap-add методом."""
    input_rms = np.sqrt(np.mean(audio ** 2))
    print(f"  RMS оригинала: {input_rms:.6f}")
    
    chunk_samples = int(CHUNK_SIZE * SAMPLE_RATE)
    overlap_samples = int(chunk_samples * OVERLAP_RATIO)
    hop_samples = chunk_samples - overlap_samples
    
    output_audio = np.zeros(len(audio))
    window_sum = np.zeros(len(audio))
    
    num_chunks = (len(audio) - chunk_samples) // hop_samples + 1
    if (num_chunks - 1) * hop_samples + chunk_samples < len(audio):
        num_chunks += 1
    
    print(f"Обрабатываю аудио с overlap-add ({num_chunks} чанков x {CHUNK_SIZE}s, overlap={OVERLAP_RATIO*100:.0f}%)...")
    
    for i in range(num_chunks):
        start = i * hop_samples
        end = start + chunk_samples
        
        # Последний чанк может выходить за границы
        if end > len(audio):
            end = len(audio)
            start = max(0, end - chunk_samples)
        
        chunk = audio[start:end]
        actual_len = len(chunk)
        
        # Паддим чанк если нужно до полного размера
        if len(chunk) < chunk_samples:
            chunk = np.pad(chunk, (0, chunk_samples - len(chunk)), mode='constant')
        
        magnitude_norm, phase = stft_spectrogram(chunk, sr=SAMPLE_RATE)
        
        mag_tensor = torch.tensor(magnitude_norm).unsqueeze(0).unsqueeze(0).float().to(device)
        
        with torch.no_grad():
            output_mag = model(mag_tensor)
        
        output_mag = output_mag.squeeze(0).squeeze(0).cpu().numpy()
        output_mag = np.clip(output_mag, 0, 1)
        
        # Паддинг до 1025 бинов
        if output_mag.shape[0] < 1025:
            output_mag_padded = np.zeros((1025, output_mag.shape[1]), dtype=output_mag.dtype)
            output_mag_padded[:output_mag.shape[0], :] = output_mag
            output_mag = output_mag_padded
        
        if phase.shape[0] != output_mag.shape[0]:
            phase_padded = np.zeros((output_mag.shape[0], phase.shape[1]), dtype=phase.dtype)
            phase_padded[:phase.shape[0], :] = phase
            phase = phase_padded
        if phase.shape[1] != output_mag.shape[1]:
            phase = phase[:, :output_mag.shape[1]]
        
        output_chunk = stft_to_audio(output_mag, phase, sr=SAMPLE_RATE)
        
        # Паддим output_chunk до размера чанка если нужно
        if len(output_chunk) < chunk_samples:
            output_chunk = np.pad(output_chunk, (0, chunk_samples - len(output_chunk)), mode='constant')
        elif len(output_chunk) > chunk_samples:
            output_chunk = output_chunk[:chunk_samples]
        
        # Берем только нужную длину
        output_chunk = output_chunk[:actual_len]
        
        # Создаем Hann окно для этого чанка
        if i == 0 and num_chunks == 1:
            chunk_window = np.ones(actual_len)
        elif i == 0:
            chunk_window = np.sin(np.linspace(0, np.pi/2, actual_len))
        elif i == num_chunks - 1:
            chunk_window = np.sin(np.linspace(np.pi/2, np.pi, actual_len))
        else:
            chunk_window = np.ones(actual_len)
        
        # Добавляем взвешенный чанк к выходу
        output_audio[start:end] += output_chunk * chunk_window
        window_sum[start:end] += chunk_window
        
        progress = (i + 1) / num_chunks * 100
        print(f"  [{progress:5.1f}%] Обработано: {end/SAMPLE_RATE:.1f}s")
    
    # Нормализуем на сумму окон
    window_sum = np.maximum(window_sum, 1e-8)
    output_audio = output_audio / window_sum
    
    return output_audio
