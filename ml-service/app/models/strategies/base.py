import io
import torch
import librosa
import soundfile as sf
import numpy as np
from abc import ABC

from app.models.utils_unet import stft_spectrogram
from app.models.model_unet_improved import ImprovedUNetSeparator


class BaseProcessingStrategy(ABC):
    """
    Базовый класс стратегии обработки аудио.
    Определяет общий шаблон обработки:
    1. Загрузка модели
    2. STFT преобразование
    3. Применение модели
    4. Пост-процессинг (инструмент-специфичный)
    5. ISTFT преобразование
    """
    
    def __init__(self, model_path: str, model_config: dict, sample_rate: int, 
                 chunk_size: int, overlap_ratio: float, device_str: str = "cuda"):
        self.model_path = model_path
        self.model_config = model_config
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.overlap_ratio = overlap_ratio
        
        if device_str == "mps":
            self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        elif device_str == "cuda":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device("cpu")
        
        self._model = None
    
    def get_instrument_name(self) -> str:
        pass

    def apply_post_processing(self, magnitude: np.ndarray, phase: np.ndarray) -> np.ndarray:
        pass
    
    def load_model(self):
        if self._model is not None:
            return self._model
        
        self._model = ImprovedUNetSeparator(**self.model_config).to(self.device)
        self._model.load_state_dict(torch.load(self.model_path, map_location=self.device))
        self._model.eval()
        
        print(f"[{self.get_instrument_name()} Model] Загружена модель из {self.model_path}")
        print(f"  Устройство: {self.device}")
        
        return self._model
    
    def _process_chunk(self, chunk_audio: np.ndarray, actual_len: int) -> np.ndarray:
        model = self.load_model()
        magnitude_norm, phase = stft_spectrogram(chunk_audio, sr=self.sample_rate)
        mag_tensor = torch.tensor(magnitude_norm).unsqueeze(0).unsqueeze(0).float().to(self.device)
        
        with torch.no_grad():
            output_mag = model(mag_tensor)
        
        output_mag = output_mag.squeeze(0).squeeze(0).cpu().numpy()
        output_audio = self.apply_post_processing(output_mag, phase)
        
        if len(output_audio) < actual_len:
            output_audio = np.pad(output_audio, (0, actual_len - len(output_audio)))
        elif len(output_audio) > actual_len:
            excess = len(output_audio) - actual_len
            start_crop = excess // 2
            output_audio = output_audio[start_crop:start_crop + actual_len]
        
        return output_audio
    
    def _apply_gain_compensation(self, audio: np.ndarray, input_rms: float) -> np.ndarray:
        output_rms = np.sqrt(np.mean(audio ** 2))
        if output_rms > 1e-6:
            gain = input_rms / output_rms
            audio = audio * gain * 0.95
        return audio
    
    def process_audio(self, audio: np.ndarray) -> np.ndarray:
        input_rms = np.sqrt(np.mean(audio ** 2))
        chunk_samples = int(self.chunk_size * self.sample_rate)

        if len(audio) < chunk_samples:
            output_audio = self._process_chunk(audio, len(audio))
        else:
            overlap_samples = int(chunk_samples * self.overlap_ratio)
            hop_samples = chunk_samples - overlap_samples
            
            output_audio = np.zeros(len(audio))
            window_sum = np.zeros(len(audio))
            
            num_chunks = (len(audio) - chunk_samples) // hop_samples + 1
            if (num_chunks - 1) * hop_samples + chunk_samples < len(audio):
                num_chunks += 1
            
            hann_window = np.hanning(chunk_samples + 2)
            
            for i in range(num_chunks):
                start = i * hop_samples
                end = start + chunk_samples
                
                if end > len(audio):
                    end = len(audio)
                    start = max(0, end - chunk_samples)
                
                chunk = audio[start:end].copy()
                actual_len = len(chunk)

                if len(chunk) < chunk_samples:
                    chunk = np.pad(chunk, (0, chunk_samples - len(chunk)), mode='constant')
                output_chunk = self._process_chunk(chunk, actual_len)
                output_chunk = output_chunk[:actual_len]
                chunk_window = hann_window[:actual_len]
                output_audio[start:end] += output_chunk * chunk_window
                window_sum[start:end] += chunk_window
            
            # Нормализуем на сумму окон
            window_sum = np.maximum(window_sum, 1e-8)
            output_audio = output_audio / window_sum
        
        # Применяем компенсацию громкости
        output_audio = self._apply_gain_compensation(output_audio, input_rms)
        
        return output_audio
    
    def process_audio_file(self, input_bytes: bytes, output_format: str = "WAV") -> io.BytesIO:
        audio, sr = librosa.load(io.BytesIO(input_bytes), sr=self.sample_rate)
        output_audio = self.process_audio(audio)

        max_val = np.max(np.abs(output_audio))
        if max_val > 1.0:
            output_audio = output_audio / max_val

        output_buf = io.BytesIO()
        sf.write(output_buf, output_audio, self.sample_rate, format=output_format)
        output_buf.seek(0)
        
        return output_buf
