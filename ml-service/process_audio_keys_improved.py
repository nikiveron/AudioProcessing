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
SAMPLE_RATE = 48000  # Единый sample rate для всех файлов


def load_model():
    """Загружает обученную модель"""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Модель не найдена: {MODEL_PATH}")
    
    # Создаём модель с теми же параметрами что и при обучении
    model = ImprovedUNetSeparator(input_size=1025, base_channels=32, dropout_rate=0.1).to(device)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    model.eval()
    
    print(f"✓ Модель загружена из {MODEL_PATH}")
    print(f"  Устройство: {device}")
    
    # Подсчёт параметров
    num_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Количество параметров: {num_params:,}")
    
    return model


def process_audio(model, input_path, output_path, chunk_size=15, debug=False, reference_path=None):
    """
    Обрабатывает аудиофайл моделью с использованием STFT.
    Сохраняет исходную фазу для восстановления качественного звука.
    
    Args:
        model: Обученная нейронная сеть
        input_path: Путь к входному аудиофайлу
        output_path: Путь для сохранения обработанного файла
        chunk_size: Размер чанка в секундах для обработки (для экономии памяти)
        debug: Выводить отладочную информацию
        reference_path: Путь к обработанному файлу для сравнения
    """
    print(f"\nЗагружаю аудио: {input_path}")
    
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Файл не найден: {input_path}")
    
    # Загружаем аудио
    audio, sr = librosa.load(input_path, sr=SAMPLE_RATE)
    print(f"✓ Аудио загружено: {len(audio)} семплов ({len(audio)/sr:.1f} сек)")
    
    # Если нужна отладка - загружаем reference
    reference_mag = None
    if debug and reference_path and os.path.exists(reference_path):
        print(f"\nЗагружаю reference: {reference_path}")
        ref_audio, _ = librosa.load(reference_path, sr=SAMPLE_RATE)
        reference_mag, _ = stft_spectrogram(ref_audio, sr)
        print(f"✓ Reference спектрограмма загружена: {reference_mag.shape}")
        print(f"  Диапазон: [{reference_mag.min():.4f}, {reference_mag.max():.4f}]")
        print(f"  Среднее: {reference_mag.mean():.4f}, Std: {reference_mag.std():.4f}")
    
    # Если аудио короче чанка, обрабатываем целиком
    if len(audio) < chunk_size * SAMPLE_RATE:
        print("Обрабатываю аудио целиком...")
        magnitude_norm, phase = stft_spectrogram(audio, sr)
        
        if debug:
            print("\n[DEBUG] Входная спектрограмма:")
            print(f"  Shape: {magnitude_norm.shape}")
            print(f"  Диапазон: [{magnitude_norm.min():.4f}, {magnitude_norm.max():.4f}]")
            print(f"  Среднее: {magnitude_norm.mean():.4f}, Std: {magnitude_norm.std():.4f}")
        
        # Добавляем batch dimension: (freq, time) → (batch=1, 1, freq, time)
        mag_tensor = torch.tensor(magnitude_norm).unsqueeze(0).unsqueeze(0).float().to(device)
        
        with torch.no_grad():
            output_mag = model(mag_tensor)
        
        # Убираем batch dimension: (batch, 1, freq, time) → (freq, time)
        output_mag = output_mag.squeeze(0).squeeze(0).cpu().numpy()
        output_mag = np.clip(output_mag, 0, 1)
        
        if debug:
            print("\n[DEBUG] Выходная спектрограмма:")
            print(f"  Shape: {output_mag.shape}")
            print(f"  Диапазон: [{output_mag.min():.4f}, {output_mag.max():.4f}]")
            print(f"  Среднее: {output_mag.mean():.4f}, Std: {output_mag.std():.4f}")
            
            if reference_mag is not None:
                diff = np.abs(output_mag - reference_mag)
                print("\n[DEBUG] Разница с reference:")
                print(f"  MAE: {diff.mean():.4f}")
                print(f"  Max diff: {diff.max():.4f}")
        
        # Паддим output_mag до 1025 частотных бинов и сохраняем time dimension
        orig_time = output_mag.shape[1]
        if output_mag.shape[0] < 1025:
            output_mag_padded = np.zeros((1025, orig_time), dtype=output_mag.dtype)
            output_mag_padded[:output_mag.shape[0], :] = output_mag
            output_mag = output_mag_padded
        
        # Кропаем или паддим фазу до match с output_mag
        if phase.shape[0] != output_mag.shape[0]:
            phase_padded = np.zeros((output_mag.shape[0], phase.shape[1]), dtype=phase.dtype)
            phase_padded[:phase.shape[0], :] = phase
            phase = phase_padded
        if phase.shape[1] != output_mag.shape[1]:
            phase = phase[:, :output_mag.shape[1]]
        
        # Восстанавливаем аудио используя исходную фазу
        output_audio = stft_to_audio(output_mag, phase, sr)
    
    else:
        # Обрабатываем по чанкам для экономии памяти
        chunk_samples = int(chunk_size * SAMPLE_RATE)
        output_audio = np.zeros_like(audio)
        
        num_chunks = (len(audio) + chunk_samples - 1) // chunk_samples
        print(f"Обрабатываю аудио по чанкам ({num_chunks} чанков x {chunk_size}s)...")
        
        for i in range(num_chunks):
            start = i * chunk_samples
            end = min(start + chunk_samples, len(audio))
            
            chunk = audio[start:end]
            magnitude_norm, phase = stft_spectrogram(chunk, sr)
            
            if debug and i == 0:
                print("\n[DEBUG] Первый чанк - входная спектрограмма:")
                print(f"  Shape: {magnitude_norm.shape}")
                print(f"  Диапазон: [{magnitude_norm.min():.4f}, {magnitude_norm.max():.4f}]")
                print(f"  Среднее: {magnitude_norm.mean():.4f}, Std: {magnitude_norm.std():.4f}")
            
            # Обработка через модель
            mag_tensor = torch.tensor(magnitude_norm).unsqueeze(0).unsqueeze(0).float().to(device)
            
            with torch.no_grad():
                output_mag = model(mag_tensor)
            
            output_mag = output_mag.squeeze(0).squeeze(0).cpu().numpy()
            output_mag = np.clip(output_mag, 0, 1)
            
            if debug and i == 0:
                print("[DEBUG] Первый чанк - выходная спектрограмма:")
                print(f"  Shape: {output_mag.shape}")
                print(f"  Диапазон: [{output_mag.min():.4f}, {output_mag.max():.4f}]")
                print(f"  Среднее: {output_mag.mean():.4f}, Std: {output_mag.std():.4f}")
            
            # Паддим output_mag до 1025 частотных бинов и сохраняем time dimension
            orig_time = output_mag.shape[1]
            if output_mag.shape[0] < 1025:
                output_mag_padded = np.zeros((1025, orig_time), dtype=output_mag.dtype)
                output_mag_padded[:output_mag.shape[0], :] = output_mag
                output_mag = output_mag_padded
            
            # Кропаем или паддим фазу до match с output_mag
            if phase.shape[0] != output_mag.shape[0]:
                phase_padded = np.zeros((output_mag.shape[0], phase.shape[1]), dtype=phase.dtype)
                phase_padded[:phase.shape[0], :] = phase
                phase = phase_padded
            if phase.shape[1] != output_mag.shape[1]:
                phase = phase[:, :output_mag.shape[1]]
            
            output_chunk = stft_to_audio(output_mag, phase, sr)
            
            # Если длина не совпадает, интерполируем
            if len(output_chunk) != len(chunk):
                output_chunk = librosa.util.pad_center(
                    output_chunk, 
                    size=len(chunk)
                )
            
            output_audio[start:end] = output_chunk[:len(chunk)]
            
            progress = (i + 1) / num_chunks * 100
            print(f"  [{progress:5.1f}%] Обработано: {end/SAMPLE_RATE:.1f}s")
    
    # Диагностика выходного аудио
    if debug:
        print("\n[DEBUG] Выходное аудио:")
        print(f"  Диапазон: [{output_audio.min():.4f}, {output_audio.max():.4f}]")
        print(f"  Среднее: {output_audio.mean():.4f}, Std: {output_audio.std():.4f}")
        print(f"  Количество нулей: {np.sum(output_audio == 0)} / {len(output_audio)}")
    
    # Нормализуем аудио если нужно
    max_val = np.max(np.abs(output_audio))
    if max_val > 1.0:
        output_audio = output_audio / max_val
        if debug:
            print(f"  Нормализовано на коэффициент: {max_val:.2f}")
    
    # Сохраняем результат
    sf.write(output_path, output_audio, sr)
    print(f"\n✓ Результат сохранён: {output_path}")
    print(f"  Длина: {len(output_audio)} семплов ({len(output_audio)/sr:.1f} сек)")


def main():
    if len(sys.argv) < 3:
        print("="*70)
        print("Обработка аудио с помощью улучшенной U-Net модели клавиш (STFT)")
        print("="*70)
        print("\nИспользование:")
        print("  python process_audio_keys_improved.py <input_file> <output_file> [--debug] [--ref <reference_file>]")
        print("\nПримеры:")
        print("  python process_audio_keys_improved.py raw.wav output.wav")
        print("  python process_audio_keys_improved.py raw.wav output.wav --debug")
        print("  python process_audio_keys_improved.py raw.wav output.wav --debug --ref processed.wav")
        print("\nТехнология: STFT с окном Ханна + сохранение исходной фазы")
        print("Модель: Improved U-Net с Attention Gates")
        print("="*70)
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    # Парсим флаги
    debug = "--debug" in sys.argv
    reference_file = None
    if "--ref" in sys.argv:
        ref_idx = sys.argv.index("--ref") + 1
        if ref_idx < len(sys.argv):
            reference_file = sys.argv[ref_idx]
    
    print("="*70)
    print("Обработка аудио клавиш улучшенной U-Net моделью (STFT)")
    if debug:
        print("[РЕЖИМ ОТЛАДКИ ВКЛЮЧЕН]")
    print("="*70)
    
    try:
        # Загружаем модель
        model = load_model()
        
        # Обрабатываем аудио
        process_audio(model, input_file, output_file, debug=debug, reference_path=reference_file)
        
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
