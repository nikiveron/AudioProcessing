import io
import os
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset

N_FFT = 2048
HOP = 512
WIN_LENGTH = 2048
WINDOW = "hann"
N_MELS = 128


def split_and_save(audio_path, save_dir, segment_duration=15.0, sample_rate=44100):
    """Split audio file into segments and save them"""
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


class AudioEffectDataset(Dataset):
    """Dataset for audio processing training"""

    def __init__(self, clean_dir, processed_dir, sample_rate=44100):
        self.sample_rate = sample_rate
        self.clean_files = sorted([
            os.path.join(clean_dir, f) for f in os.listdir(clean_dir) if f.endswith(".wav")
        ])
        self.processed_files = sorted([
            os.path.join(processed_dir, f) for f in os.listdir(processed_dir) if f.endswith(".wav")
        ])
        assert len(self.clean_files) == len(self.processed_files)

    def _mel(self, audio):
        spec = librosa.feature.melspectrogram(
            y=audio,
            sr=self.sample_rate,
            n_fft=N_FFT,
            hop_length=HOP,
            win_length=WIN_LENGTH,
            window=WINDOW,
            n_mels=N_MELS,
            power=2.0
        )
        db = librosa.power_to_db(spec, ref=np.max)
        norm = (db + 80) / 80
        return norm

    def __len__(self):
        return len(self.clean_files)

    def __getitem__(self, idx):
        clean_audio, _ = librosa.load(self.clean_files[idx], sr=self.sample_rate)
        processed_audio, _ = librosa.load(self.processed_files[idx], sr=self.sample_rate)

        clean_mel = self._mel(clean_audio)
        processed_mel = self._mel(processed_audio)

        return (
            torch.tensor(clean_mel).unsqueeze(0).float(),
            torch.tensor(processed_mel).unsqueeze(0).float()
        )


def spectral_loss(output, target, sr=44100):
    """Calculate spectral loss between output and target"""
    def mel_to_wave(mel_tensor):
        mel_db = mel_tensor * 80 - 80
        mel_power = librosa.db_to_power(mel_db.cpu().numpy())
        wav = librosa.feature.inverse.mel_to_audio(
            mel_power,
            sr=sr,
            n_fft=N_FFT,
            hop_length=HOP,
            win_length=WIN_LENGTH,
            window=WINDOW,
            n_iter=5,
            length=None
        )
        return torch.tensor(wav)

    loss = 0
    out = output.squeeze(1)
    tgt = target.squeeze(1)

    for o, t in zip(out, tgt):
        w_o = mel_to_wave(o)
        w_t = mel_to_wave(t)

        min_len = min(len(w_o), len(w_t))
        w_o, w_t = w_o[:min_len], w_t[:min_len]

        stft_kwargs = dict(
            n_fft=N_FFT,
            hop_length=HOP,
            win_length=WIN_LENGTH,
            window=torch.hann_window(WIN_LENGTH),
            return_complex=True
        )

        mag_o = torch.abs(torch.stft(w_o, **stft_kwargs))
        mag_t = torch.abs(torch.stft(w_t, **stft_kwargs))

        loss += F.l1_loss(mag_o, mag_t)

    return loss / output.size(0)


def process_single_file(model, input_bytes, device, sample_rate=44100):
    """Process single audio file through the model

    Args:
    ----
        model: Trained GRU model
        input_bytes: Raw audio file bytes
        device: PyTorch device (cuda/cpu)
        sample_rate: Sample rate for audio processing

    Returns:
    -------
        BytesIO object containing processed audio in WAV format

    """
    y, sr = librosa.load(io.BytesIO(input_bytes), sr=sample_rate)

    spec = librosa.feature.melspectrogram(
        y=y,
        sr=sr,
        n_fft=N_FFT,
        hop_length=HOP,
        win_length=WIN_LENGTH,
        window=WINDOW,
        n_mels=N_MELS
    )

    spec_db = librosa.power_to_db(spec, ref=np.max)
    spec_norm = (spec_db + 80) / 80

    spec_tensor = torch.tensor(spec_norm).unsqueeze(0).unsqueeze(0).float().to(device)

    model.eval()
    with torch.no_grad():
        output = model(spec_tensor)

    output = output.squeeze().cpu().numpy()
    output_db = output * 80 - 80
    output_power = librosa.db_to_power(output_db)

    y_out = librosa.feature.inverse.mel_to_audio(
        output_power,
        sr=sr,
        n_fft=N_FFT,
        hop_length=HOP,
        win_length=WIN_LENGTH,
        window=WINDOW,
        n_iter=64
    )

    buf = io.BytesIO()
    sf.write(buf, y_out, sr, format='WAV')
    buf.seek(0)
    return buf


def apply_genre_effect(audio_buffer: io.BytesIO, genre: str, device, sample_rate=44100) -> io.BytesIO:
    """Apply genre-specific audio effects

    Args:
    ----
        audio_buffer: BytesIO object with audio data
        genre: Genre name (Classic, Jazz, Rock, etc.)
        device: PyTorch device
        sample_rate: Sample rate

    Returns:
    -------
        BytesIO object with processed audio

    """
    try:
        audio_buffer.seek(0)
        y, sr = librosa.load(audio_buffer, sr=sample_rate)

        # Normalize genre name for comparison
        genre_lower = str(genre).lower()

        if "classic" in genre_lower:
            # Classic music: enhance mid-range frequencies
            y = librosa.effects.trim(y, top_db=20)[0]
            D = librosa.stft(y)
            S = np.abs(D)
            freqs = librosa.fft_frequencies(sr=sr, n_fft=len(D))
            mid_mask = (freqs > 500) & (freqs < 4000)
            S[mid_mask] *= 1.1
            y = librosa.istft(S)

        elif "jazz" in genre_lower:
            # Jazz: smooth compression and slight boost
            y = y * 1.05
            y = np.clip(y, -1, 1)

        elif "rock" in genre_lower:
            # Rock: boost high frequencies and add slight distortion
            D = librosa.stft(y)
            S = np.abs(D)
            freqs = librosa.fft_frequencies(sr=sr, n_fft=len(D))
            high_mask = freqs > 3000
            S[high_mask] *= 1.15
            y = librosa.istft(S)
            y = np.clip(y * 1.1, -1, 1)

        buf = io.BytesIO()
        sf.write(buf, y, sr, format='WAV')
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"[Genre Effect] Error applying {genre} effect: {e}")
        audio_buffer.seek(0)
        return audio_buffer


def apply_instrument_effect(audio_buffer: io.BytesIO, instrument: str, device, sample_rate=44100) -> io.BytesIO:
    """Apply instrument-specific audio effects

    Args:
    ----
        audio_buffer: BytesIO object with audio data
        instrument: Instrument name (Guitar, Piano, Vocal, etc.)
        device: PyTorch device
        sample_rate: Sample rate

    Returns:
    -------
        BytesIO object with processed audio

    """
    try:
        audio_buffer.seek(0)
        y, sr = librosa.load(audio_buffer, sr=sample_rate)

        # Normalize instrument name for comparison
        instrument_lower = str(instrument).lower()

        if "guitar" in instrument_lower:
            # Guitar: boost mid-frequencies and add sustain
            D = librosa.stft(y)
            S = np.abs(D)
            freqs = librosa.fft_frequencies(sr=sr, n_fft=len(D))
            mid_mask = (freqs > 300) & (freqs < 3000)
            S[mid_mask] *= 1.1
            y = librosa.istft(S)

        elif "piano" in instrument_lower:
            # Piano: preserve dynamics, clear highs
            D = librosa.stft(y)
            S = np.abs(D)
            freqs = librosa.fft_frequencies(sr=sr, n_fft=len(D))
            high_mask = freqs > 4000
            S[high_mask] *= 1.05
            y = librosa.istft(S)

        elif "vocal" in instrument_lower:
            # Vocal: enhance presence peak (around 2-4kHz)
            D = librosa.stft(y)
            S = np.abs(D)
            freqs = librosa.fft_frequencies(sr=sr, n_fft=len(D))
            presence_mask = (freqs > 2000) & (freqs < 4000)
            S[presence_mask] *= 1.15
            y = librosa.istft(S)

        buf = io.BytesIO()
        sf.write(buf, y, sr, format='WAV')
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"[Instrument Effect] Error applying {instrument} effect: {e}")
        audio_buffer.seek(0)
        return audio_buffer(
            mel_power,
            sr=sr,
            n_fft=N_FFT,
            hop_length=HOP,
            win_length=WIN_LENGTH,
            window=WINDOW,
            n_iter=5,
            length=None
        )
        return torch.tensor(wav)

        loss = 0
        out = output.squeeze(1)
        tgt = target.squeeze(1)

        for o, t in zip(out, tgt):
            w_o = mel_to_wave(o)
            w_t = mel_to_wave(t)

            min_len = min(len(w_o), len(w_t))
            w_o, w_t = w_o[:min_len], w_t[:min_len]

            stft_kwargs = dict(
                n_fft=N_FFT,
                hop_length=HOP,
                win_length=WIN_LENGTH,
                window=torch.hann_window(WIN_LENGTH),
                return_complex=True
            )

            mag_o = torch.abs(torch.stft(w_o, **stft_kwargs))
            mag_t = torch.abs(torch.stft(w_t, **stft_kwargs))

            loss += F.l1_loss(mag_o, mag_t)

        return loss / output.size(0)

def process_single_file(model, input_bytes, device, sample_rate=44100):
    y, sr = librosa.load(io.BytesIO(input_bytes), sr=sample_rate)

    spec = librosa.feature.melspectrogram(
        y=y,
        sr=sr,
        n_fft=N_FFT,
        hop_length=HOP,
        win_length=WIN_LENGTH,
        window=WINDOW,
        n_mels=N_MELS
    )

    spec_db = librosa.power_to_db(spec, ref=np.max)
    spec_norm = (spec_db + 80) / 80

    spec_tensor = torch.tensor(spec_norm).unsqueeze(0).unsqueeze(0).float().to(device)

    model.eval()
    with torch.no_grad():
        output = model(spec_tensor)

    output = output.squeeze().cpu().numpy()
    output_db = output * 80 - 80
    output_power = librosa.db_to_power(output_db)

    y_out = librosa.feature.inverse.mel_to_audio(
        output_power,
        sr=sr,
        n_fft=N_FFT,
        hop_length=HOP,
        win_length=WIN_LENGTH,
        window=WINDOW,
        n_iter=64
    )

    buf = io.BytesIO()
    sf.write(buf, y_out, sr, format='WAV')
    buf.seek(0)
    return buf
