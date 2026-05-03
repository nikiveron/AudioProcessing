#!/usr/bin/env python3
"""
Скрипт для обработки аудио бас-гитары с помощью улучшенной U-Net модели.
Использование: python process_bass_with_model.py input_audio.wav output_audio.wav

Алгоритм аналогичен process_audio_keys_improved_clean.py:
- Overlap-add обработка для плавных переходов
- Без агрессивного шумоподавления - только модель
"""

import os
import sys
import torch
import librosa
import soundfile as sf
import numpy as np
from scipy import signal

from app.model_unet_improved import ImprovedUNetSeparator
from app.utils_unet import stft_spectrogram, stft_to_audio

device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
MODEL_PATH = "model_weights_bass_improved_unet.pth"
SAMPLE_RATE = 48000


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
    """
    print(f"\nЗагружаю аудио: {input_path}")
    
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Файл не найден: {input_path}")
    
    audio, sr = librosa.load(input_path, sr=SAMPLE_RATE)
    print(f"✓ Аудио загружено: {len(audio)} семплов ({len(audio)/sr:.1f} сек)")
    
    if len(audio) < chunk_size * SAMPLE_RATE:
        print("Обрабатываю аудио целиком...")
        
        # Сохраняем RMS оригинала для компенсации громкости
        input_rms = np.sqrt(np.mean(audio ** 2))
        print(f"  RMS оригинала: {input_rms:.6f}")
        
        magnitude_norm, phase = stft_spectrogram(audio, sr)
        
        mag_tensor = torch.tensor(magnitude_norm).unsqueeze(0).unsqueeze(0).float().to(device)
        
        with torch.no_grad():
            output_mag = model(mag_tensor)
        
        output_mag = output_mag.squeeze(0).squeeze(0).cpu().numpy()
        output_mag = np.clip(output_mag, 0, 1)
        
        
        # Паддинг до 1025 бинов
        orig_time = output_mag.shape[1]
        if output_mag.shape[0] < 1025:
            output_mag_padded = np.zeros((1025, orig_time), dtype=output_mag.dtype)
            output_mag_padded[:output_mag.shape[0], :] = output_mag
            output_mag = output_mag_padded
        
        if phase.shape[0] != output_mag.shape[0]:
            phase_padded = np.zeros((output_mag.shape[0], phase.shape[1]), dtype=phase.dtype)
            phase_padded[:phase.shape[0], :] = phase
            phase = phase_padded
        if phase.shape[1] != output_mag.shape[1]:
            phase = phase[:, :output_mag.shape[1]]
        
        output_audio = stft_to_audio(output_mag, phase, sr)
        
        nyquist = sr / 2
        cutoff = 5000
        b, a = signal.butter(4, cutoff / nyquist, btype='low')
        output_audio = signal.filtfilt(b, a, output_audio)
        

        output_rms = np.sqrt(np.mean(output_audio ** 2))
        if output_rms > 1e-6:
            gain = input_rms / output_rms
            output_audio = output_audio * gain * 0.95
            print(f"  Компенсация громкости: gain={gain:.2f}")
        print(f"  RMS выхода: {np.sqrt(np.mean(output_audio ** 2)):.6f}")
    
    else:
        # Сохраняем RMS оригинала для компенсации громкости
        input_rms = np.sqrt(np.mean(audio ** 2))
        print(f"  RMS оригинала: {input_rms:.6f}")
        
        # OVERLAP-ADD обработка с плавными переходами
        chunk_samples = int(chunk_size * SAMPLE_RATE)
        overlap_samples = int(chunk_samples * 0.25)  # 25% перекрытие
        hop_samples = chunk_samples - overlap_samples
        
        output_audio = np.zeros(len(audio))
        window_sum = np.zeros(len(audio))
        
        num_chunks = (len(audio) - overlap_samples) // hop_samples
        if num_chunks * hop_samples + overlap_samples < len(audio):
            num_chunks += 1
            
        print(f"Обрабатываю аудио с overlap-add ({num_chunks} чанков x {chunk_size}s, overlap=25%)...")
        
        # Hann окно для каждого чанка
        hann_window = np.hanning(chunk_samples + 2)  # +2 для краев
        
        for i in range(num_chunks):
            start = i * hop_samples
            end = min(start + chunk_samples, len(audio))
            
            # Корректируем start для последнего чанка
            if end - start < chunk_samples:
                start = max(0, end - chunk_samples)
            
            chunk = audio[start:end].copy()
            actual_len = len(chunk)
            
            # Паддим чанк до полного размера
            if len(chunk) < chunk_samples:
                chunk = np.pad(chunk, (0, chunk_samples - len(chunk)), mode='constant')
            
            magnitude_norm, phase = stft_spectrogram(chunk, sr)
            
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
            
            output_chunk = stft_to_audio(output_mag, phase, sr)
            
            # Паддим output_chunk
            if len(output_chunk) < chunk_samples:
                output_chunk = np.pad(output_chunk, (0, chunk_samples - len(output_chunk)), mode='constant')
            elif len(output_chunk) > chunk_samples:
                output_chunk = output_chunk[:chunk_samples]
            
            # Применяем Hann окно для плавных переходов
            chunk_window = hann_window[:actual_len]
            
            # Добавляем взвешенный чанк
            output_audio[start:end] += output_chunk[:actual_len] * chunk_window
            window_sum[start:end] += chunk_window
            
            progress = (i + 1) / num_chunks * 100
            print(f"  [{progress:5.1f}%] Обработано: {end/SAMPLE_RATE:.1f}s")
        
        # Нормализуем на сумму окон
        window_sum = np.maximum(window_sum, 1e-8)
        output_audio = output_audio / window_sum
        
        # Low-pass фильтр для удаления высокочастотных шумов (бас < 5kHz)
        nyquist = sr / 2
        cutoff = 5000  # 5 kHz для баса
        b, a = signal.butter(4, cutoff / nyquist, btype='low')
        output_audio = signal.filtfilt(b, a, output_audio)
        
        # Компенсация громкости (make-up gain)
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
        print("Обработка аудио бас-гитары улучшенной U-Net моделью")
        print("="*70)
        print("\nИспользование:")
        print("  python process_bass_with_model.py <input> <output>")
        print("\nПримеры:")
        print("  python process_bass_with_model.py raw.wav output.wav")
        print("\nМодель: Improved U-Net с Attention Gates")
        print("Без пост-процессинга шумоподавления")
        print("="*70)
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    print("="*70)
    print("Обработка аудио бас-гитары улучшенной U-Net моделью")
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
