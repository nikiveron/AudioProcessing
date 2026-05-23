#!/usr/bin/env python3
"""
Скрипт для обработки аудио электрогитары с помощью улучшенной U-Net модели.
Использование: python process_eg.py input_audio.wav output_audio.wav

Алгоритм:
- Overlap-add обработка для плавных переходов
- Spectral smoothing для уменьшения шумов
- Spectral gating для подавления тихих частот
- Частотная коррекция для электрогитары
"""

import os
import sys
import torch
import librosa
import soundfile as sf
import numpy as np
from scipy import signal

from app.models.model_unet_improved import ImprovedUNetSeparator
from app.models.utils_unet import stft_spectrogram, stft_to_audio

device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
MODEL_PATH = "model_weights_eg_improved_unet.pth"
SAMPLE_RATE = 48000


def spectral_smoothing(magnitude, smoothing_factor=0.4):
    """
    Применяет частотное сглаживание для уменьшения шумов.
    Использует скользящее среднее по частоте и времени.
    """
    smoothed = magnitude.copy()
    
    # Вертикальное сглаживание (по частоте)
    for t in range(magnitude.shape[1]):
        for f in range(1, magnitude.shape[0] - 1):
            smoothed[f, t] = (
                magnitude[f-1, t] * smoothing_factor * 0.5 +
                magnitude[f, t] * (1 - smoothing_factor) +
                magnitude[f+1, t] * smoothing_factor * 0.5
            )
    
    # Горизонтальное сглаживание (по времени)
    for f in range(magnitude.shape[0]):
        for t in range(1, magnitude.shape[1] - 1):
            smoothed[f, t] = (
                smoothed[f, t-1] * smoothing_factor * 0.3 +
                smoothed[f, t] * (1 - smoothing_factor * 0.3) +
                smoothed[f, t+1] * smoothing_factor * 0.3
            ) / (1 + smoothing_factor * 0.6)
    
    return smoothed


def spectral_gating(magnitude, threshold=0.02, floor=0.1):
    """
    Spectral gating - подавление частотных бинов ниже порога.
    """
    gated = magnitude.copy()
    
    for t in range(magnitude.shape[1]):
        frame = magnitude[:, t]
        dynamic_threshold = np.percentile(frame, 15)
        
        for f in range(magnitude.shape[0]):
            if frame[f] < dynamic_threshold:
                gain = floor + (1 - floor) * (frame[f] / (dynamic_threshold + 1e-8))
                gated[f, t] = frame[f] * gain
    
    return gated


def frequency_weighting(magnitude, low_freq_boost=1.2, high_freq_attenuation=0.85):
    """
    Частотная коррекция для электрогитары.
    """
    freq_bins = magnitude.shape[0]
    freq_curve = np.ones(freq_bins)
    
    # Низкие частоты (0-0.3) - усиление
    for i in range(int(freq_bins * 0.3)):
        freq_curve[i] = 1.0 + (low_freq_boost - 1.0) * (1 - i / (freq_bins * 0.3))
    
    # Высокие частоты (0.6-1.0) - ослабление
    for i in range(int(freq_bins * 0.6), freq_bins):
        norm_pos = (i - freq_bins * 0.6) / (freq_bins * 0.4)
        freq_curve[i] = high_freq_attenuation + (1 - high_freq_attenuation) * (1 - norm_pos)
    
    weighted = magnitude * freq_curve[:, np.newaxis]
    return np.clip(weighted, 0, 1)


def load_model():
    """Загружает обученную модель"""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Модель не найдена: {MODEL_PATH}")
    
    model = ImprovedUNetSeparator(input_size=1025, base_channels=32, dropout_rate=0.1).to(device)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    model.eval()
    
    print(f"✓ Модель загружена из {MODEL_PATH}")
    print(f"  Устройство: {device}")
    
    num_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Количество параметров: {num_params:,}")
    
    return model


def process_audio(model, input_path, output_path, chunk_size=15, reference_path=None):
    """
    Обрабатывает аудиофайл моделью с overlap-add для плавных переходов.
    Применяет spectral smoothing и gating для уменьшения шумов.
    """
    print(f"\nЗагружаю аудио: {input_path}")
    
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Файл не найден: {input_path}")
    
    audio, sr = librosa.load(input_path, sr=SAMPLE_RATE)
    print(f"✓ Аудио загружено: {len(audio)} семплов ({len(audio)/sr:.1f} сек)")
    
    # Сохраняем RMS оригинала для компенсации громкости
    input_rms = np.sqrt(np.mean(audio ** 2))
    print(f"  RMS оригинала: {input_rms:.6f}")
    
    if len(audio) < chunk_size * SAMPLE_RATE:
        print("Обрабатываю аудио целиком...")
        
        magnitude_norm, phase = stft_spectrogram(audio, sr)
        
        mag_tensor = torch.tensor(magnitude_norm).unsqueeze(0).unsqueeze(0).float().to(device)
        
        with torch.no_grad():
            output_mag = model(mag_tensor)
        
        output_mag = output_mag.squeeze(0).squeeze(0).cpu().numpy()
        output_mag = np.clip(output_mag, 0, 1)
        
        # === POST-PROCESSING: Spectral cleanup ===
        print("  Применяю spectral smoothing...")
        output_mag = spectral_smoothing(output_mag, smoothing_factor=0.25)
        
        print("  Применяю spectral gating...")
        output_mag = spectral_gating(output_mag, threshold=0.03, floor=0.15)
        
        print("  Применяю частотную коррекцию...")
        output_mag = frequency_weighting(output_mag, low_freq_boost=1.1, high_freq_attenuation=0.75)
        # =========================================
        
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
        
        output_audio = stft_to_audio(output_mag, phase, sr)
        
        # === Фильтр для электрогитары: low-pass 10kHz вместо 5kHz ===
        nyquist = sr / 2
        cutoff = 10000  # 10 kHz для электрогитары (вместо 5kHz для баса)
        b, a = signal.butter(2, cutoff / nyquist, btype='low')
        output_audio = signal.filtfilt(b, a, output_audio)
        # ============================================================
        
        output_rms = np.sqrt(np.mean(output_audio ** 2))
        if output_rms > 1e-6:
            gain = input_rms / output_rms
            output_audio = output_audio * gain * 0.95
            print(f"  Компенсация громкости: gain={gain:.2f}")
        print(f"  RMS выхода: {np.sqrt(np.mean(output_audio ** 2)):.6f}")
    
    else:
        # OVERLAP-ADD обработка с плавными переходами
        chunk_samples = int(chunk_size * SAMPLE_RATE)
        overlap_samples = int(chunk_samples * 0.25)
        hop_samples = chunk_samples - overlap_samples
        
        output_audio = np.zeros(len(audio))
        window_sum = np.zeros(len(audio))
        
        num_chunks = (len(audio) - overlap_samples) // hop_samples
        if num_chunks * hop_samples + overlap_samples < len(audio):
            num_chunks += 1
            
        print(f"Обрабатываю аудио с overlap-add ({num_chunks} чанков x {chunk_size}s, overlap=25%)...")
        
        hann_window = np.hanning(chunk_samples + 2)
        
        for i in range(num_chunks):
            start = i * hop_samples
            end = min(start + chunk_samples, len(audio))
            
            if end - start < chunk_samples:
                start = max(0, end - chunk_samples)
            
            chunk = audio[start:end].copy()
            actual_len = len(chunk)
            
            if len(chunk) < chunk_samples:
                chunk = np.pad(chunk, (0, chunk_samples - len(chunk)), mode='constant')
            
            magnitude_norm, phase = stft_spectrogram(chunk, sr)
            
            mag_tensor = torch.tensor(magnitude_norm).unsqueeze(0).unsqueeze(0).float().to(device)
            
            with torch.no_grad():
                output_mag = model(mag_tensor)
            
            output_mag = output_mag.squeeze(0).squeeze(0).cpu().numpy()
            output_mag = np.clip(output_mag, 0, 1)
            
            # === POST-PROCESSING: Spectral cleanup ===
            output_mag = spectral_smoothing(output_mag, smoothing_factor=0.25)
            output_mag = spectral_gating(output_mag, threshold=0.03, floor=0.15)
            output_mag = frequency_weighting(output_mag, low_freq_boost=1.1, high_freq_attenuation=0.75)
            # =========================================
            
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
            
            output_chunk = stft_to_audio(output_mag, phase, sr)
            
            if len(output_chunk) < chunk_samples:
                output_chunk = np.pad(output_chunk, (0, chunk_samples - len(output_chunk)), mode='constant')
            elif len(output_chunk) > chunk_samples:
                output_chunk = output_chunk[:chunk_samples]
            
            chunk_window = hann_window[:actual_len]
            output_audio[start:end] += output_chunk[:actual_len] * chunk_window
            window_sum[start:end] += chunk_window
            
            progress = (i + 1) / num_chunks * 100
            print(f"  [{progress:5.1f}%] Обработано: {end/SAMPLE_RATE:.1f}s")
        
        window_sum = np.maximum(window_sum, 1e-8)
        output_audio = output_audio / window_sum
        
        # === Фильтр для электрогитары: low-pass 10kHz вместо 5kHz ===
        nyquist = sr / 2
        cutoff = 10000  # 10 kHz для электрогитары
        b, a = signal.butter(2, cutoff / nyquist, btype='low')
        output_audio = signal.filtfilt(b, a, output_audio)
        # ============================================================
        
        output_rms = np.sqrt(np.mean(output_audio ** 2))
        if output_rms > 1e-6:
            gain = input_rms / output_rms
            output_audio = output_audio * gain * 0.95
            print(f"  Компенсация громкости: gain={gain:.2f}")
        print(f"  RMS выхода: {np.sqrt(np.mean(output_audio ** 2)):.6f}")
    
    # Нормализуем выходное аудио
    max_val = np.max(np.abs(output_audio))
    if max_val > 1.0:
        output_audio = output_audio / max_val
    
    sf.write(output_path, output_audio, sr)
    print(f"\n✓ Результат сохранён: {output_path}")
    print(f"  Длина: {len(output_audio)} семплов ({len(output_audio)/sr:.1f} сек)")


def main():
    if len(sys.argv) < 3:
        print("="*70)
        print("Обработка аудио электрогитары улучшенной U-Net моделью")
        print("="*70)
        print("\nИспользование:")
        print("  python process_eg.py <input> <output>")
        print("\nПримеры:")
        print("  python process_eg.py raw.wav output.wav")
        print("\nМодель: Improved U-Net с Attention Gates")
        print("Пост-процессинг: spectral smoothing + gating + частотная коррекция")
        print("="*70)
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    print("="*70)
    print("Обработка аудио электрогитары улучшенной U-Net моделью")
    print("="*70)
    
    try:
        model = load_model()
        process_audio(model, input_file, output_file)
        
        print("\n" + "="*70)
        print("✓ Обработка успешно завершена!")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
