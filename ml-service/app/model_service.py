import io

import torch

from .config import DEVICE, ENABLE_PARAMETER_PROCESSING, MODEL_PATH
from .model import GRUSeparator
from .utils import apply_genre_effect, apply_instrument_effect, process_single_file

device = torch.device(DEVICE if torch.cuda.is_available() else "cpu")
model = GRUSeparator().to(device)

try:
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    print("[Model] Weights loaded successfully")
    model.eval()
except FileNotFoundError:
    print("[Model] WARNING: Weights not found. Run training first.")
except Exception as e:
    print(f"[Model] ERROR loading weights: {e}")


def process_audio_file(
    input_bytes: bytes,
    genre: str = None,
    instrument: str = None
) -> io.BytesIO:
    """Process audio file with optional genre and instrument parameters

    Args:
    ----
        input_bytes: Raw audio file bytes
        genre: Music genre (optional)
        instrument: Music instrument (optional)

    Returns:
    -------
        BytesIO object containing processed audio in WAV format

    """
    result_buf = process_single_file(model, input_bytes, device)

    # Apply additional processing based on parameters if enabled
    if ENABLE_PARAMETER_PROCESSING:
        try:
            if genre:
                print(f"[Processing] Applying genre effect: {genre}")
                result_buf = apply_genre_effect(result_buf, genre, device)

            if instrument:
                print(f"[Processing] Applying instrument effect: {instrument}")
                result_buf = apply_instrument_effect(result_buf, instrument, device)
        except Exception as e:
            print(f"[Processing] Warning: Failed to apply effects: {e}. Continuing with base output.")

    return result_buf
