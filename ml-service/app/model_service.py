import torch
import io
from .model import GRUSeparator
from .utils import process_single_file
from .config import MODEL_PATH, DEVICE

device = torch.device(DEVICE if torch.cuda.is_available() else "cpu")
model = GRUSeparator().to(device)

try:
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    print("[Model] Weights loaded")
    model.eval()
except FileNotFoundError:
    print("[Model] Weights not found. Run training first.")


def process_audio_file(input_bytes: bytes) -> io.BytesIO:
    result_buf = process_single_file(model, input_bytes, device)
    return result_buf
