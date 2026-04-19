import os
import time
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from app.model import GRUSeparator
from app.utils import split_and_save, AudioEffectDataset, spectral_loss

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

BASE_DIR = "data"
CLEAN_DIR = os.path.join(BASE_DIR, "clean")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")

os.makedirs(CLEAN_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

clean_files = [
    "data/eg 2 even though i walk.wav",
    "data/eg 2 till the walls.wav",
    "data/eg 2 fathers house.wav"
]
processed_files = [
    "data/eg 2 even though i walk render 001.wav",
    "data/eg 2 till the walls render 001.wav",
    "data/eg 2 fathers house render 001.wav"
]

print("=== Splitting audio files into segments ===")

for clean_path, proc_path in zip(clean_files, processed_files):
    split_and_save(clean_path, CLEAN_DIR)
    split_and_save(proc_path, PROCESSED_DIR)

print("Segmentation finished.\n")

dataset = AudioEffectDataset(CLEAN_DIR, PROCESSED_DIR)
loader = DataLoader(dataset, batch_size=4, shuffle=True, num_workers=0)

model = GRUSeparator().to(device)
criterion = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

def train_epoch(model, loader, criterion, optimizer, epoch, num_epochs):
    model.train()
    total_loss = 0

    print(f"\nEpoch {epoch}/{num_epochs}")
    print("-" * 50)

    for batch_i, (clean_mel, processed_mel) in enumerate(loader, 1):

        clean_mel = clean_mel.to(device)
        processed_mel = processed_mel.to(device)

        optimizer.zero_grad()

        t0 = time.time()
        output = model(clean_mel)
        loss_mse = criterion(output, processed_mel)
        loss_spec = spectral_loss(
            output.detach(),
            processed_mel.detach()
        )

        loss = loss_mse + 0.5 * loss_spec

        loss.backward()
        optimizer.step()

        batch_time = time.time() - t0

        total_loss += loss.item()

        print(
            f"Batch {batch_i}/{len(loader)}  "
            f"| mse={loss_mse.item():.4f}  "
            f"spec={loss_spec.item():.4f}  "
            f"total={loss.item():.4f}  "
            f"[{batch_time:.1f}s]"
        )

    avg = total_loss / len(loader)
    print(f"Epoch finished: avg loss = {avg:.4f}")
    return avg


num_epochs = 10
print("=== Training started ===")

for epoch in range(1, num_epochs+1):
    avg_loss = train_epoch(model, loader, criterion, optimizer, epoch, num_epochs)
    print(f"Epoch {epoch+1}/{num_epochs}  Loss: {avg_loss:.4f}")

torch.save(model.state_dict(), "model_weights.pth")
print("\nModel saved to model_weights.pth")
