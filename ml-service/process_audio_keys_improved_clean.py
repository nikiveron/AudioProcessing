"""
Скрипт для обработки аудио с помощью улучшенной U-Net модели клавиш (ЧИСТЫЙ режим)
Использование: python process_audio_keys_improved_clean.py input_audio.wav output_audio.wav

Без агрессивного шумоподавления - только модель + overlap-add для плавных переходов
"""

import os
import sys
import torch
import librosa
import soundfile as sf
import numpy as np

from app.model_unet_improved import ImprovedUNetSeparator
from app.utils_unet import stft_spectrogram, stft_to_audio

device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
MODEL_PATH = "model_weights_keys_improved_unet.pth"
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


def process_audio(model, input_path, output_path, chunk_size=15, debug=False, reference_path=None):
    """
    Обрабатывает аудиофайл моделью с overlap-add для плавных переходов.
    Без агрессивного шумоподавления.
    """
    print(f"\nЗагружаю аудио: {input_path}")
    
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Файл не найден: {input_path}")
    
    audio, sr = librosa.load(input_path, sr=SAMPLE_RATE)
    print(f"✓ Аудио загружено: {len(audio)} семплов ({len(audio)/sr:.1f} сек)")
    
    reference_mag = None
    if debug and reference_path and os.path.exists(reference_path):
        print(f"\nЗагружаю reference: {reference_path}")
        ref_audio, _ = librosa.load(reference_path, sr=SAMPLE_RATE)
        reference_mag, _ = stft_spectrogram(ref_audio, sr)
    
    if len(audio) < chunk_size * SAMPLE_RATE:
        print("Обрабатываю аудио целиком...")
        magnitude_norm, phase = stft_spectrogram(audio, sr)
        
        if debug:
            print(f"\n[DEBUG] Вход: shape={magnitude_norm.shape}, range=[{magnitude_norm.min():.4f}, {magnitude_norm.max():.4f}]")
        
        mag_tensor = torch.tensor(magnitude_norm).unsqueeze(0).unsqueeze(0).float().to(device)
        
        with torch.no_grad():
            output_mag = model(mag_tensor)
        
        output_mag = output_mag.squeeze(0).squeeze(0).cpu().numpy()
        output_mag = np.clip(output_mag, 0, 1)
        
        if debug:
            print(f"[DEBUG] Выход: shape={output_mag.shape}, range=[{output_mag.min():.4f}, {output_mag.max():.4f}]")
        
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
    
    else:
        # OVERLAP-ADD обработка с плавными переходами
        chunk_samples = int(chunk_size * SAMPLE_RATE)
        overlap_samples = int(chunk_samples * 0.3)  # 30% перекрытие для более плавных переходов
        hop_samples = chunk_samples - overlap_samples
        
        # Используем взвешенное сложение с Hann окном
        output_audio = np.zeros(len(audio))
        window_sum = np.zeros(len(audio))  # Сумма окон для нормализации
        
        num_chunks = (len(audio) - chunk_samples) // hop_samples + 1
        # Добавляем последний чанк если нужно
        if (num_chunks - 1) * hop_samples + chunk_samples < len(audio):
            num_chunks += 1
            
        print(f"Обрабатываю аудио с overlap-add ({num_chunks} чанков x {chunk_size}s, overlap=30%)...")
        
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
            
            magnitude_norm, phase = stft_spectrogram(chunk, sr)
            
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
            
            output_chunk = stft_to_audio(output_mag, phase, sr)
            
            # Паддим output_chunk до размера чанка если нужно
            if len(output_chunk) < chunk_samples:
                output_chunk = np.pad(output_chunk, (0, chunk_samples - len(output_chunk)), mode='constant')
            elif len(output_chunk) > chunk_samples:
                output_chunk = output_chunk[:chunk_samples]
            
            # Берем только нужную длину
            output_chunk = output_chunk[:actual_len]
            
            # Создаем Hann окно для этого чанка
            if i == 0 and num_chunks == 1:
                # Только один чанк - без окна
                chunk_window = np.ones(actual_len)
            elif i == 0:
                # Первый чанк - только правый край окна
                chunk_window = np.sin(np.linspace(0, np.pi/2, actual_len))
            elif i == num_chunks - 1:
                # Последний чанк - только левый край окна
                chunk_window = np.sin(np.linspace(np.pi/2, np.pi, actual_len))
            else:
                # Средние чанки - полное Hann окно на overlap регионах
                chunk_window = np.ones(actual_len)
            
            # Добавляем взвешенный чанк к выходу
            output_audio[start:end] += output_chunk * chunk_window
            window_sum[start:end] += chunk_window
            
            progress = (i + 1) / num_chunks * 100
            print(f"  [{progress:5.1f}%] Обработано: {end/SAMPLE_RATE:.1f}s")
        
        # Нормализуем на сумму окон
        window_sum = np.maximum(window_sum, 1e-8)  # Защита от деления на 0
        output_audio = output_audio / window_sum
    
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
        print("Обработка аудио с улучшенной U-Net моделью (ЧИСТЫЙ режим)")
        print("="*70)
        print("\nИспользование:")
        print("  python process_audio_keys_improved_clean.py <input> <output> [--debug]")
        print("\nПримеры:")
        print("  python process_audio_keys_improved_clean.py raw.wav output.wav")
        print("  python process_audio_keys_improved_clean.py raw.wav output.wav --debug")
        print("\nМодель: Improved U-Net с Attention Gates")
        print("Без пост-процессинга шумоподавления")
        print("="*70)
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    debug = "--debug" in sys.argv
    
    print("="*70)
    print("Обработка аудио клавиш улучшенной U-Net моделью")
    print("[РЕЖИМ: ЧИСТЫЙ - без шумоподавления]")
    if debug:
        print("[РЕЖИМ ОТЛАДКИ ВКЛЮЧЕН]")
    print("="*70)
    
    try:
        model = load_model()
        process_audio(model, input_file, output_file, debug=debug)
        
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
