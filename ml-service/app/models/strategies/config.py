import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
WEIGHTS_DIR = os.path.join(BASE_DIR, "models", "models_weights")

SAMPLE_RATE = 48000
MODEL_CONFIG = {"input_size": 1025, "base_channels": 32, "dropout_rate": 0.1}
CHUNK_SIZE = 15
OVERLAP_RATIO = 0.3
DEVICE = os.getenv("DEVICE", "cuda")

AG_MODEL_PATH = os.path.join(WEIGHTS_DIR, os.getenv("AG_MODEL_FILE", "model_weights_ag.pth"))
BASS_MODEL_PATH = os.path.join(WEIGHTS_DIR, os.getenv("BASS_MODEL_FILE", "model_weights_bass.pth"))
EG_MODEL_PATH = os.path.join(WEIGHTS_DIR, os.getenv("EG_MODEL_FILE", "model_weights_eg.pth"))
KEYS_MODEL_PATH = os.path.join(WEIGHTS_DIR, os.getenv("KEYS_MODEL_FILE", "model_weights_keys.pth"))

POST_PROCESSING_AG = {
    "smoothing_factor": 0.15,
    "gating_threshold": 0.04,
    "gating_floor": 0.2,
    "low_freq_boost": 1.15,
    "high_freq_attenuation": 0.92,
    "lowpass_cutoff": 10000
}

POST_PROCESSING_BASS = {
    "lowpass_cutoff": 5000,
    "lowpass_order": 4
}
