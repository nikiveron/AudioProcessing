import os
import time
import glob
from pathlib import Path
import random

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from app.model_unet_improved import ImprovedUNetSeparator, ImprovedComplexUNetSeparator
from app.utils_unet import split_and_save, AudioEffectDataset, SSIMLoss

device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")


BASE_DIR = "data"
KEYS_RAW_DIR = os.path.join(BASE_DIR, "keys", "raw")
KEYS_PROCESSED_DIR = os.path.join(BASE_DIR, "keys", "processed")

# Директории для сегментов
SEGMENTS_RAW_DIR = os.path.join(BASE_DIR, "keys_segments", "raw")
SEGMENTS_PROCESSED_DIR = os.path.join(BASE_DIR, "keys_segments", "processed")

os.makedirs(SEGMENTS_RAW_DIR, exist_ok=True)
os.makedirs(SEGMENTS_PROCESSED_DIR, exist_ok=True)

print("="*70)
print("Обучение УЛУЧШЕННОЙ U-Net модели обработки клавиш")
print("="*70)

# Конфигурация
USE_COMPLEX = False  # True для ImprovedComplexUNet, False для ImprovedUNet
MODEL_TYPE = "improved_complex" if USE_COMPLEX else "improved_unet"

# Получаем список файлов и сопоставляем пары
def match_file_pairs(raw_dir, processed_dir):
    raw_files = glob.glob(os.path.join(raw_dir, "*.wav"))
    processed_files = glob.glob(os.path.join(processed_dir, "*.wav"))
    
    pairs = []
    
    for raw_path in raw_files:
        raw_name = Path(raw_path).stem
        base_name = raw_name.replace('_raw', '')
        
        for proc_path in processed_files:
            proc_name = Path(proc_path).stem
            
            if base_name in proc_name and '_processed' in proc_name:
                pairs.append((raw_path, proc_path))
                print(f"  ✓ Пара: {Path(raw_path).name} → {Path(proc_path).name}")
                break
    
    return pairs

print("\nСопоставление пар raw → processed:")
file_pairs = match_file_pairs(KEYS_RAW_DIR, KEYS_PROCESSED_DIR)

if not file_pairs:
    print("ERROR: Не найдено пар файлов!")
    exit(1)

print(f"\nНайдено пар: {len(file_pairs)}")

print("\n" + "="*70)
print("ЭТАП 1: Разбиение аудио на 15-секундные сегменты")
print("="*70)

SEGMENT_DURATION = 15.0
SAMPLE_RATE = 48000

raw_segments = glob.glob(os.path.join(SEGMENTS_RAW_DIR, "*.wav"))
processed_segments = glob.glob(os.path.join(SEGMENTS_PROCESSED_DIR, "*.wav"))

if len(raw_segments) > 0 and len(processed_segments) > 0:
    print("\n✓ Сегменты уже созданы ранее!")
    print(f"  Найдено сегментов сырых записей: {len(raw_segments)}")
    print(f"  Найдено сегментов обработанных записей: {len(processed_segments)}")
else:
    print("\nСегменты не найдены, создаю новые...")
    print("\nОбработка сырых записей...")
    for raw_file, _ in file_pairs:
        split_and_save(raw_file, SEGMENTS_RAW_DIR, segment_duration=SEGMENT_DURATION, sample_rate=SAMPLE_RATE)

    print("\nОбработка обработанных записей...")
    for _, proc_file in file_pairs:
        split_and_save(proc_file, SEGMENTS_PROCESSED_DIR, segment_duration=SEGMENT_DURATION, sample_rate=SAMPLE_RATE)

print("\n" + "="*70)
print("ЭТАП 2: Подготовка датасета")
print("="*70)

dataset = AudioEffectDataset(SEGMENTS_RAW_DIR, SEGMENTS_PROCESSED_DIR, sample_rate=SAMPLE_RATE, use_complex=USE_COMPLEX)
print(f"\nОбщее количество сегментов: {len(dataset)}")

# Уменьшенный batch size для MPS
BATCH_SIZE = 2
ACCUMULATION_STEPS = 1  # Без аккумуляции для скорости

# pin_memory не поддерживается на MPS
use_pin_memory = device.type == 'cuda'
loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0, pin_memory=use_pin_memory)
print(f"Размер батча: {BATCH_SIZE}")
print(f"Количество батчей: {len(loader)}")

print("\n" + "="*70)
print("ЭТАП 3: Инициализация модели")
print("="*70)

if USE_COMPLEX:
    model = ImprovedComplexUNetSeparator(input_size=1025, base_channels=64).to(device)
    print("Модель: ImprovedComplexUNetSeparator")
else:
    model = ImprovedUNetSeparator(input_size=1025, base_channels=32, dropout_rate=0.1).to(device)
    print("Модель: ImprovedUNetSeparator (base_channels=32)")

print(f"Используется устройство: {device}")

# Подсчёт параметров
num_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"Количество параметров: {num_params:,}")

# Оптимизатор Adam с более простым scheduler
initial_lr = 1e-3

optimizer = torch.optim.Adam(
    model.parameters(), 
    lr=initial_lr,
    betas=(0.9, 0.999),
    eps=1e-8
)

# StepLR scheduler - проще и быстрее
scheduler = torch.optim.lr_scheduler.StepLR(
    optimizer,
    step_size=15,  # Уменьшаем LR каждые 15 эпох
    gamma=0.5
)

# Функции потерь
criterion_l1 = nn.L1Loss()
criterion_ssim = SSIMLoss(window_size=11)

# Улучшенная комбинированная функция потерь
class CombinedLoss(nn.Module):
    """
    Комбинированная функция потерь с динамическим весом SSIM.
    """
    def __init__(self, l1_weight=0.8, ssim_weight=0.2):
        super().__init__()
        self.l1_weight = l1_weight
        self.ssim_weight = ssim_weight
        self.l1 = nn.L1Loss()
        self.ssim = SSIMLoss(window_size=11)
        
    def forward(self, output, target):
        l1_loss = self.l1(output, target)
        ssim_loss = self.ssim(output, target)
        
        # Edge enhancement loss
        # Градиенты по частоте и времени
        grad_freq_out = output[:, :, 1:, :] - output[:, :, :-1, :]
        grad_freq_target = target[:, :, 1:, :] - target[:, :, :-1, :]
        edge_loss = nn.L1Loss()(grad_freq_out, grad_freq_target)
        
        return (
            self.l1_weight * l1_loss + 
            self.ssim_weight * ssim_loss +
            0.1 * edge_loss  # Небольшой вес для edge loss
        )

criterion = CombinedLoss(l1_weight=0.8, ssim_weight=0.2)

print(f"\nОптимизатор: Adam (lr={initial_lr})")
print(f"Scheduler: StepLR (step_size=15, gamma=0.5)")
print(f"Функция потерь: Combined (L1 + SSIM + Edge)")

# Gradient scaler для mixed precision (если поддерживается)
use_amp = device.type == 'cuda'
if use_amp:
    scaler = torch.cuda.amp.GradScaler()
    print("Mixed Precision: включено")
else:
    scaler = None
    print("Mixed Precision: выключено")

# Функция для обучения эпохи
def train_epoch(model, loader, optimizer, criterion, epoch, num_epochs, scheduler=None):
    model.train()
    total_loss = 0
    total_l1 = 0
    total_ssim = 0

    print(f"\nEpoch {epoch}/{num_epochs}")
    print("-" * 70)

    for batch_i, (clean, processed) in enumerate(loader, 1):
        clean = clean.to(device)
        processed = processed.to(device)

        t0 = time.time()
        
        output = model(clean)
        
        # Кропаем processed до размеров output
        if output.shape != processed.shape:
            min_freq = min(output.shape[2], processed.shape[2])
            min_time = min(output.shape[3], processed.shape[3])
            output = output[:, :, :min_freq, :min_time]
            processed = processed[:, :, :min_freq, :min_time]
        
        loss = criterion(output, processed)
        loss_l1 = nn.L1Loss()(output, processed)
        loss_ssim = SSIMLoss(window_size=11)(output, processed)
        
        optimizer.zero_grad()
        loss.backward()
        
        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        batch_time = time.time() - t0
        total_loss += loss.item()
        total_l1 += loss_l1.item()
        total_ssim += loss_ssim.item()

        if batch_i % 10 == 0 or batch_i == len(loader):
            current_lr = optimizer.param_groups[0]['lr']
            print(
                f"Batch {batch_i:3d}/{len(loader):3d}  "
                f"| L1={loss_l1.item():.4f}  "
                f"| SSIM={loss_ssim.item():.4f}  "
                f"| Total={loss.item():.4f}  "
                f"| LR={current_lr:.6f}  "
                f"| Time={batch_time:.1f}s"
            )

    avg_loss = total_loss / len(loader)
    avg_l1 = total_l1 / len(loader)
    avg_ssim = total_ssim / len(loader)
    
    print(f"Epoch {epoch} завершен: средняя потеря = {avg_loss:.4f} (L1={avg_l1:.4f}, SSIM={avg_ssim:.4f})")
    return avg_loss


# Обучение модели
print("\n" + "="*70)
print("ЭТАП 4: Обучение модели")
print("="*70)

MAX_EPOCHS = 50
TARGET_LOSS = 0.02

epoch_losses = []
best_loss = float('inf')
best_model_state = None
patience_counter = 0
early_stop_patience = 10

start_time = time.time()
early_stop = False

try:
    for epoch in range(1, MAX_EPOCHS + 1):
        avg_loss = train_epoch(
            model, loader, optimizer, criterion, 
            epoch, MAX_EPOCHS, 
            scheduler=scheduler
        )
        epoch_losses.append(avg_loss)
        
        # Scheduler step после эпохи
        scheduler.step()
        
        # Сохраняем лучшую модель
        if avg_loss < best_loss:
            best_loss = avg_loss
            best_model_state = model.state_dict().copy()
            patience_counter = 0
            print(f"  💾 Сохранена лучшая модель (loss={best_loss:.4f})")
        else:
            patience_counter += 1
            if patience_counter >= early_stop_patience:
                print(f"\n⏹️  Ранняя остановка: нет улучшений {early_stop_patience} эпох")
                early_stop = True
                break
        
        # Проверка на целевой порог
        if avg_loss <= TARGET_LOSS:
            print(f"\n🎯 Достигнут целевой порог потери ({avg_loss:.4f} <= {TARGET_LOSS})!")
            early_stop = True
            break
        
        # Каждые 5 эпох выводим статистику
        if epoch % 5 == 0:
            current_lr = optimizer.param_groups[0]['lr']
            print(f"\n>>> Прогресс: {epoch}/{MAX_EPOCHS} эпох завершено")
            print(f"    Текущий LR: {current_lr:.6f}")

except KeyboardInterrupt:
    print("\n\nОбучение прервано пользователем.")
except Exception as e:
    print(f"\n\nОшибка при обучении: {e}")
    import traceback
    traceback.print_exc()
    raise

# Восстанавливаем лучшую модель
if best_model_state is not None:
    print(f"\n� Восстановлена лучшая модель (loss={best_loss:.4f})")
    model.load_state_dict(best_model_state)

total_time = time.time() - start_time

# Сохранение весов модели
print("\n" + "="*70)
print("ЭТАП 5: Сохранение модели")
print("="*70)

model_type_str = "improved_complex" if USE_COMPLEX else "improved_unet"
model_path = f"model_weights_keys_{model_type_str}.pth"
torch.save(model.state_dict(), model_path)
print(f"\n✓ Модель сохранена: {model_path}")

# Выводим статистику
print("\n" + "="*70)
print("ИТОГОВАЯ СТАТИСТИКА")
print("="*70)

actual_epochs = len(epoch_losses)
print(f"Количество эпох: {actual_epochs}")
if early_stop:
    print(f"Ранняя остановка")
else:
    print(f"Завершено по достижении {MAX_EPOCHS} эпох")

print(f"Начальная потеря: {epoch_losses[0]:.4f}")
print(f"Финальная потеря: {epoch_losses[-1]:.4f}")
print(f"Улучшение: {((epoch_losses[0] - epoch_losses[-1]) / epoch_losses[0] * 100):.1f}%")
print(f"Общее время обучения: {total_time/60:.1f} минут ({total_time:.0f} секунд)")
print(f"Среднее время на эпоху: {total_time/actual_epochs:.1f} сек")
print(f"Лучшая потеря: {best_loss:.4f}")
print("\n✓ Обучение завершено успешно!")
print("="*70)
