import os
import librosa
import soundfile as sf
import numpy as np
import torch
import torch.nn.functional as F
from pathlib import Path
from torch.utils.data import Dataset
import io

# STFT параметры с оконным преобразованием
N_FFT = 2048
HOP = 512
WIN_LENGTH = 2048
WINDOW = "hann"  # Hann window - оптимальное окно для STFT

# Нормализация спектров
SPEC_MIN = 1e-9  # Минимум для логарифма
SPEC_MAX = 1.0   # Максимум нормализации


def split_and_save(audio_path, save_dir, segment_duration=15.0, sample_rate=48000):
    """
    Разбивает аудиофайл на сегменты и сохраняет их.
    
    Args:
        audio_path: Путь к входному аудиофайлу
        save_dir: Директория для сохранения сегментов
        segment_duration: Длина каждого сегмента в секундах
        sample_rate: Частота дискретизации (по умолчанию 48000 Hz)
    """
    os.makedirs(save_dir, exist_ok=True)
    print(f"Loading {audio_path} ...")

    y, sr = librosa.load(audio_path, sr=sample_rate)
    samples_per_segment = int(sr * segment_duration)
    total_segments = len(y) // samples_per_segment

    for i in range(total_segments):
        segment = y[i * samples_per_segment:(i + 1) * samples_per_segment]
        sf.write(os.path.join(save_dir, f'segment_{Path(audio_path).stem}_{i:04d}.wav'),
                 segment, sr)

    print(f"Saved {total_segments} segments to {save_dir}")


def stft_spectrogram(audio, sr=48000, n_fft=N_FFT, hop_length=HOP, win_length=WIN_LENGTH, window=WINDOW):
    """
    Преобразование аудио в STFT спектрограмму с сохранением фазы.
    Использует оконное преобразование Ханна для гладких переходов.
    
    Args:
        audio: Аудиосигнал (time,)
        
    Returns:
        magnitude: Амплитуда STFT нормализованная (freq, time)
        phase: Фаза STFT (freq, time)
    """
    # STFT с окном Ханна
    D = librosa.stft(
        audio,
        n_fft=n_fft,
        hop_length=hop_length,
        win_length=win_length,
        window=window,
        center=True
    )
    
    # Разделяем на амплитуду и фазу
    magnitude = np.abs(D)
    phase = np.angle(D)
    
    # Нормализация через логарифмическую шкалу (оригинальная версия)
    # top_db=80 даёт лучший динамический диапазон для музыки
    magnitude_db = librosa.power_to_db(magnitude ** 2, ref=1.0, top_db=80)
    
    # Нормализация к [0, 1]
    magnitude_norm = (magnitude_db + 80) / 80
    magnitude_norm = np.clip(magnitude_norm, 0, 1)
    
    return magnitude_norm, phase


def stft_to_audio(magnitude_norm, phase, sr=48000, n_fft=N_FFT, hop_length=HOP, win_length=WIN_LENGTH, window=WINDOW):
    """
    Восстановление аудио из STFT спектрограммы и фазы.
    Использует исходную фазу для сохранения качества звука.
    
    Args:
        magnitude_norm: Нормализованная амплитуда (freq, time)
        phase: Сохранённая фаза (freq, time)
        
    Returns:
        audio: Восстановленное аудио (time,)
    """
    # Денормализуем амплитуду (инверсия к кодированию)
    # Используем тот же диапазон 80 dB как в stft_spectrogram для консистентности
    magnitude_db = magnitude_norm * 80 - 80
    # Используем тот же ref=1.0 для консистентности!
    magnitude = librosa.db_to_power(magnitude_db, ref=1.0) ** 0.5
    
    # Восстанавливаем комплексную спектрограмму, используя сохранённую фазу
    D_reconstructed = magnitude * np.exp(1j * phase)
    
    # Обратное STFT с окном Ханна
    audio = librosa.istft(
        D_reconstructed,
        hop_length=hop_length,
        win_length=win_length,
        window=window,
        center=True
    )
    
    return audio


class AudioEffectDataset(Dataset):
    """
    Датасет для обучения на STFT спектрограммах с сохранением фазы.
    Фаза берётся от исходного сигнала и не обучается.
    """
    
    def __init__(self, clean_dir, processed_dir, sample_rate=48000):
        self.sample_rate = sample_rate
        self.clean_files = sorted([
            os.path.join(clean_dir, f) for f in os.listdir(clean_dir) if f.endswith(".wav")
        ])
        self.processed_files = sorted([
            os.path.join(processed_dir, f) for f in os.listdir(processed_dir) if f.endswith(".wav")
        ])
        assert len(self.clean_files) == len(self.processed_files), \
            f"Кол-во файлов не совпадает: clean={len(self.clean_files)}, processed={len(self.processed_files)}"

    def __len__(self):
        return len(self.clean_files)

    def __getitem__(self, idx):
        """
        Возвращает кортеж (clean_spec, processed_spec).
        Фаза не используется для обучения, только амплитуда.
        """
        clean_audio, _ = librosa.load(self.clean_files[idx], sr=self.sample_rate)
        processed_audio, _ = librosa.load(self.processed_files[idx], sr=self.sample_rate)

        # STFT спектрограммы (только амплитуда для обучения)
        clean_mag, _ = stft_spectrogram(clean_audio, sr=self.sample_rate)
        processed_mag, _ = stft_spectrogram(processed_audio, sr=self.sample_rate)

        return (
            torch.tensor(clean_mag).unsqueeze(0).float(),      # (1, freq, time)
            torch.tensor(processed_mag).unsqueeze(0).float()   # (1, freq, time)
        )


def spectral_loss(output, target, sr=48000, n_fft=N_FFT):
    """
    Спектральная потеря между выходом модели и целевой спектрограммой.
    Без частотных весов - используем равномерную потерю для избежания шумов.
    
    Args:
        output: Output spectrogram (batch, 1, freq, time)
        target: Target spectrogram (batch, 1, freq, time)
        sr: Sample rate (default: 48000)
        n_fft: FFT size (default: 2048)
        
    Returns:
        L1 loss между спектрограммами
    """
    # Убираем channel dimension если есть
    out = output.squeeze(1) if output.dim() == 4 else output  # (batch, freq, time)
    tgt = target.squeeze(1) if target.dim() == 4 else target  # (batch, freq, time)
    
    # Clamp значения в валидный диапазон [0, 1]
    out = torch.clamp(out, min=0, max=1)
    tgt = torch.clamp(tgt, min=0, max=1)
    
    # Простая L1 потеря без весов - чтобы не усиливать шумы
    loss = F.l1_loss(out, tgt)
    
    return loss


def process_single_file(model, input_bytes, device, sample_rate=48000):
    """
    Обработка одного аудиофайла моделью.
    Сохраняет исходную фазу для лучшего восстановления звука.
    """
    y, sr = librosa.load(io.BytesIO(input_bytes), sr=sample_rate)

    # Получаем STFT с сохранением фазы
    magnitude_norm, phase = stft_spectrogram(y, sr=sr)
    
    # Преобразуем в тензор для модели
    mag_tensor = torch.tensor(magnitude_norm).unsqueeze(0).unsqueeze(0).float().to(device)

    model.eval()
    with torch.no_grad():
        output_mag = model(mag_tensor)

    # Возвращаем в numpy и убираем batch/channel dims
    output_mag = output_mag.squeeze(0).squeeze(0).cpu().numpy()
    output_mag = np.clip(output_mag, 0, 1)
    
    # Восстанавливаем аудио используя исходную фазу
    y_out = stft_to_audio(output_mag, phase, sr=sr)
    
    # Сохраняем в BytesIO
    buf = io.BytesIO()
    sf.write(buf, y_out, sr, format='WAV')
    buf.seek(0)
    return buf
