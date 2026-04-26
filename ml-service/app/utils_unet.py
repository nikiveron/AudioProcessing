import os
import librosa
import soundfile as sf
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path
from torch.utils.data import Dataset
import io

# STFT параметры
N_FFT = 2048
HOP = 512
WIN_LENGTH = 2048
WINDOW = "hann"

# Нормализация
SPEC_MIN = 1e-5
SPEC_MAX = 1.0


def split_and_save(audio_path, save_dir, segment_duration=15.0, sample_rate=48000):
    """Разбивает аудиофайл на сегменты и сохраняет их."""
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
    Преобразование аудио в STFT спектрограмму.
    Возвращает magnitude и phase для совместимости.
    """
    D = librosa.stft(
        audio,
        n_fft=n_fft,
        hop_length=hop_length,
        win_length=win_length,
        window=window,
        center=True
    )
    
    magnitude = np.abs(D)
    phase = np.angle(D)
    
    # Логарифмическая нормализация
    magnitude_db = librosa.power_to_db(magnitude ** 2, ref=1.0, top_db=80)
    magnitude_norm = (magnitude_db + 80) / 80
    magnitude_norm = np.clip(magnitude_norm, 0, 1)
    
    return magnitude_norm, phase


def stft_to_audio(magnitude_norm, phase, sr=48000, n_fft=N_FFT, hop_length=HOP, win_length=WIN_LENGTH, window=WINDOW):
    """Восстановление аудио из STFT спектрограммы и фазы."""
    # Денормализация
    magnitude_db = magnitude_norm * 80 - 80
    magnitude = librosa.db_to_power(magnitude_db, ref=1.0) ** 0.5
    
    # Восстанавливаем комплексную спектрограмму
    D_reconstructed = magnitude * np.exp(1j * phase)
    
    # Обратное STFT
    audio = librosa.istft(
        D_reconstructed,
        hop_length=hop_length,
        win_length=win_length,
        window=window,
        center=True
    )
    
    return audio


def complex_stft(audio, sr=48000, n_fft=N_FFT, hop_length=HOP, win_length=WIN_LENGTH, window=WINDOW):
    """
    Complex STFT - возвращает real и imag части.
    
    Returns:
        real: (freq, time)
        imag: (freq, time)
    """
    D = librosa.stft(
        audio,
        n_fft=n_fft,
        hop_length=hop_length,
        win_length=win_length,
        window=window,
        center=True
    )
    
    real = np.real(D)
    imag = np.imag(D)
    
    # Нормализация
    magnitude = np.abs(D)
    magnitude_db = librosa.power_to_db(magnitude ** 2, ref=1.0, top_db=80)
    scale = (magnitude_db + 80) / 80
    scale = np.clip(scale, 0, 1)
    
    # Применяем масштаб к real и imag
    phase = np.angle(D)
    real_scaled = scale * np.cos(phase)
    imag_scaled = scale * np.sin(phase)
    
    return real_scaled, imag_scaled


def complex_istft(real, imag, sr=48000, n_fft=N_FFT, hop_length=HOP, win_length=WIN_LENGTH, window=WINDOW):
    """
    Обратное Complex STFT.
    
    Args:
        real: (freq, time)
        imag: (freq, time)
    """
    # Восстанавливаем комплексное число
    D = real + 1j * imag
    
    # Денормализация (инверсия к complex_stft)
    magnitude = np.abs(D)
    phase = np.angle(D)
    
    magnitude_db = magnitude * 80 - 80
    magnitude_linear = librosa.db_to_power(magnitude_db, ref=1.0) ** 0.5
    
    D_reconstructed = magnitude_linear * np.exp(1j * phase)
    
    audio = librosa.istft(
        D_reconstructed,
        hop_length=hop_length,
        win_length=win_length,
        window=window,
        center=True
    )
    
    return audio


class AudioEffectDataset(Dataset):
    """Датасет для обучения на STFT спектрограммах."""
    
    def __init__(self, clean_dir, processed_dir, sample_rate=48000, use_complex=False):
        self.sample_rate = sample_rate
        self.use_complex = use_complex
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
        clean_audio, _ = librosa.load(self.clean_files[idx], sr=self.sample_rate)
        processed_audio, _ = librosa.load(self.processed_files[idx], sr=self.sample_rate)

        if self.use_complex:
            # Complex STFT: 2 канала (real, imag)
            clean_real, clean_imag = complex_stft(clean_audio, sr=self.sample_rate)
            processed_real, processed_imag = complex_stft(processed_audio, sr=self.sample_rate)
            
            clean_input = np.stack([clean_real, clean_imag], axis=0)  # (2, freq, time)
            processed_target = np.stack([processed_real, processed_imag], axis=0)  # (2, freq, time)
        else:
            # Magnitude STFT: 1 канал
            clean_mag, _ = stft_spectrogram(clean_audio, sr=self.sample_rate)
            processed_mag, _ = stft_spectrogram(processed_audio, sr=self.sample_rate)
            
            clean_input = np.expand_dims(clean_mag, axis=0)  # (1, freq, time)
            processed_target = np.expand_dims(processed_mag, axis=0)  # (1, freq, time)

        return (
            torch.tensor(clean_input, dtype=torch.float32),
            torch.tensor(processed_target, dtype=torch.float32)
        )


class SSIMLoss(nn.Module):
    """
    SSIM (Structural Similarity Index) Loss.
    Сохраняет структуру спектрограммы лучше чем MSE.
    """
    def __init__(self, window_size=11, size_average=True):
        super().__init__()
        self.window_size = window_size
        self.size_average = size_average
        self.channel = 1
        self.window = self._create_window(window_size, self.channel)

    def _create_window(self, window_size, channel):
        gauss = torch.arange(window_size).float() - (window_size - 1) / 2
        gauss = gauss ** 2 / (2 * 0.5 ** 2)
        gauss = torch.exp(-gauss)
        gauss = gauss / gauss.sum()
        
        _1D_window = gauss.unsqueeze(1)
        _2D_window = _1D_window.mm(_1D_window.t()).float().unsqueeze(0).unsqueeze(0)
        
        return _2D_window.expand(channel, 1, window_size, window_size).contiguous()

    def forward(self, img1, img2):
        """
        Args:
            img1: (batch, channel, freq, time)
            img2: (batch, channel, freq, time)
        """
        window = self.window.to(img1.device)
        mu1 = F.conv2d(img1, window, padding=self.window_size//2, groups=self.channel)
        mu2 = F.conv2d(img2, window, padding=self.window_size//2, groups=self.channel)

        mu1_sq = mu1.pow(2)
        mu2_sq = mu2.pow(2)
        mu1_mu2 = mu1 * mu2

        sigma1_sq = F.conv2d(img1*img1, window, padding=self.window_size//2, groups=self.channel) - mu1_sq
        sigma2_sq = F.conv2d(img2*img2, window, padding=self.window_size//2, groups=self.channel) - mu2_sq
        sigma12 = F.conv2d(img1*img2, window, padding=self.window_size//2, groups=self.channel) - mu1_mu2

        C1 = 0.01 ** 2
        C2 = 0.03 ** 2

        ssim_map = ((2*mu1_mu2 + C1)*(2*sigma12 + C2)) / ((mu1_sq + mu2_sq + C1)*(sigma1_sq + sigma2_sq + C2))

        if self.size_average:
            return 1 - ssim_map.mean()
        else:
            return 1 - ssim_map.mean(1).mean(1).mean(1)


def spectral_loss(output, target, sr=48000, n_fft=N_FFT):
    """Spectral loss с акцентом на транзиенты."""
    out = output.squeeze(1) if output.dim() == 4 else output
    tgt = target.squeeze(1) if target.dim() == 4 else target
    
    out = torch.clamp(out, min=0, max=1)
    tgt = torch.clamp(tgt, min=0, max=1)
    
    # L1 loss
    loss = F.l1_loss(out, tgt)
    
    return loss


def complex_spectral_loss(output, target):
    """
    Spectral loss для комплексных значений.
    output/target: (batch, 2, freq, time) - [real, imag]
    """
    out_real = output[:, 0, :, :]
    out_imag = output[:, 1, :, :]
    tgt_real = target[:, 0, :, :]
    tgt_imag = target[:, 1, :, :]
    
    # L1 loss для real и imag частей
    loss_real = F.l1_loss(out_real, tgt_real)
    loss_imag = F.l1_loss(out_imag, tgt_imag)
    
    return loss_real + loss_imag


def process_single_file(model, input_bytes, device, sample_rate=48000, use_complex=False):
    """Обработка одного аудиофайла моделью."""
    y, sr = librosa.load(io.BytesIO(input_bytes), sr=sample_rate)

    if use_complex:
        # Complex STFT
        real, imag = complex_stft(y, sr=sr)
        input_tensor = torch.tensor(np.stack([real, imag], axis=0)).unsqueeze(0).float().to(device)
    else:
        # Magnitude STFT
        magnitude_norm, phase = stft_spectrogram(y, sr=sr)
        input_tensor = torch.tensor(magnitude_norm).unsqueeze(0).unsqueeze(0).float().to(device)

    model.eval()
    with torch.no_grad():
        output = model(input_tensor)

    if use_complex:
        # Complex output
        output = output.squeeze(0).cpu().numpy()  # (2, freq, time)
        y_out = complex_istft(output[0], output[1], sr=sr)
    else:
        # Magnitude output
        output_mag = output.squeeze(0).squeeze(0).cpu().numpy()
        output_mag = np.clip(output_mag, 0, 1)
        y_out = stft_to_audio(output_mag, phase, sr=sr)
    
    # Сохраняем в BytesIO
    buf = io.BytesIO()
    sf.write(buf, y_out, sr, format='WAV')
    buf.seek(0)
    return buf
