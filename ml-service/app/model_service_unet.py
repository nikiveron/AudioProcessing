import torch
import io
import librosa
import soundfile as sf
import numpy as np

from .model_unet_improved import ImprovedUNetSeparator
from .utils_unet import stft_spectrogram, stft_to_audio

MODEL_PATH = "model_weights_keys_improved_unet.pth"
DEVICE = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
SAMPLE_RATE = 48000

device = torch.device(DEVICE)
model = None


def load_model():
    """Загружает модель при первом вызове"""
    global model
    if model is None:
        model = ImprovedUNetSeparator(input_size=1025, base_channels=32, dropout_rate=0.1).to(device)
        try:
            model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
            print(f"[Model] Improved UNet weights loaded from {MODEL_PATH}")
            model.eval()
        except FileNotFoundError:
            print(f"[Model] Weights not found: {MODEL_PATH}")
            raise
    return model


def apply_overlap_add(model, audio, sr, chunk_size=15, overlap_ratio=0.3):
    """
    Обрабатывает аудио с помощью overlap-add метода для плавных переходов.
    """
    chunk_samples = int(chunk_size * sr)
    overlap_samples = int(chunk_samples * overlap_ratio)
    hop_samples = chunk_samples - overlap_samples
    
    output_audio = np.zeros(len(audio))
    window_sum = np.zeros(len(audio))
    
    num_chunks = (len(audio) - chunk_samples) // hop_samples + 1
    if (num_chunks - 1) * hop_samples + chunk_samples < len(audio):
        num_chunks += 1
    
    for i in range(num_chunks):
        start = i * hop_samples
        end = start + chunk_samples
        
        if end > len(audio):
            end = len(audio)
            start = max(0, end - chunk_samples)
        
        chunk = audio[start:end]
        actual_len = len(chunk)
        
        if len(chunk) < chunk_samples:
            chunk = np.pad(chunk, (0, chunk_samples - len(chunk)), mode='constant')
        
        magnitude_norm, phase = stft_spectrogram(chunk, sr=sr)
        
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
        
        output_chunk = stft_to_audio(output_mag, phase, sr=sr)
        
        if len(output_chunk) < chunk_samples:
            output_chunk = np.pad(output_chunk, (0, chunk_samples - len(output_chunk)), mode='constant')
        elif len(output_chunk) > chunk_samples:
            output_chunk = output_chunk[:chunk_samples]
        
        output_chunk = output_chunk[:actual_len]
        
        # Hann окно для плавных переходов
        if i == 0 and num_chunks == 1:
            chunk_window = np.ones(actual_len)
        elif i == 0:
            chunk_window = np.sin(np.linspace(0, np.pi/2, actual_len))
        elif i == num_chunks - 1:
            chunk_window = np.sin(np.linspace(np.pi/2, np.pi, actual_len))
        else:
            chunk_window = np.ones(actual_len)
        
        output_audio[start:end] += output_chunk * chunk_window
        window_sum[start:end] += chunk_window
    
    window_sum = np.maximum(window_sum, 1e-8)
    output_audio = output_audio / window_sum
    
    return output_audio


def process_audio_file_improved(input_bytes: bytes, output_format: str = "WAV") -> io.BytesIO:
    """
    Обрабатывает аудиофайл с помощью Improved UNet модели с overlap-add.
    
    Args:
        input_bytes: Входные данные аудиофайла
        output_format: Формат выходного файла (WAV, MP3, FLAC, etc.)
    """
    model = load_model()
    
    y, sr = librosa.load(io.BytesIO(input_bytes), sr=SAMPLE_RATE)
    
    if len(y) < 15 * SAMPLE_RATE:
        # Короткое аудио - обрабатываем целиком
        magnitude_norm, phase = stft_spectrogram(y, sr=sr)
        
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
        
        y_out = stft_to_audio(output_mag, phase, sr=sr)
    else:
        # Длинное аудио - overlap-add обработка
        y_out = apply_overlap_add(model, y, sr)
    
    # Нормализация
    max_val = np.max(np.abs(y_out))
    if max_val > 1.0:
        y_out = y_out / max_val
    
    buf = io.BytesIO()
    sf.write(buf, y_out, sr, format=output_format)
    buf.seek(0)
    return buf
