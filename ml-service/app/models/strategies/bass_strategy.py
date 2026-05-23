import numpy as np
from scipy import signal

from app.models.strategies.base import BaseProcessingStrategy
from app.models.utils_unet import stft_to_audio
from app.models.strategies.config import SAMPLE_RATE, MODEL_CONFIG, CHUNK_SIZE, OVERLAP_RATIO, DEVICE, BASS_MODEL_PATH, POST_PROCESSING_BASS


class BassProcessingStrategy(BaseProcessingStrategy):

    def __init__(self):
        super().__init__(
            model_path=str(BASS_MODEL_PATH),
            model_config=MODEL_CONFIG,
            sample_rate=SAMPLE_RATE,
            chunk_size=CHUNK_SIZE,
            overlap_ratio=OVERLAP_RATIO,
            device_str=DEVICE
        )

    def get_instrument_name(self) -> str:
        return "Bass"

    def apply_post_processing(self, magnitude: np.ndarray, phase: np.ndarray) -> np.ndarray:
        lowpass_cutoff = POST_PROCESSING_BASS.get("lowpass_cutoff", 5000)
        lowpass_order = POST_PROCESSING_BASS.get("lowpass_order", 4)

        if magnitude.shape[0] < 1025:
            magnitude_padded = np.zeros((1025, magnitude.shape[1]), dtype=magnitude.dtype)
            magnitude_padded[:magnitude.shape[0], :] = magnitude
            magnitude = magnitude_padded

        if phase.shape[0] != magnitude.shape[0]:
            phase_padded = np.zeros((magnitude.shape[0], phase.shape[1]), dtype=phase.dtype)
            phase_padded[:phase.shape[0], :] = phase
            phase = phase_padded
        if phase.shape[1] != magnitude.shape[1]:
            phase = phase[:, :magnitude.shape[1]]

        audio = stft_to_audio(magnitude, phase, sr=self.sample_rate, n_fft=2048, hop_length=512, win_length=2048, window="hann")

        nyquist = self.sample_rate / 2
        b, a = signal.butter(lowpass_order, lowpass_cutoff / nyquist, btype='low')
        audio = signal.filtfilt(b, a, audio)

        return audio
