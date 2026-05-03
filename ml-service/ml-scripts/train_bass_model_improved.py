import os
import time
import glob
from pathlib import Path
import shutil

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from app.model_unet_improved import ImprovedUNetSeparator, ImprovedComplexUNetSeparator
from app.utils_unet import split_and_save, AudioEffectDataset, SSIMLoss

device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")


BASE_DIR = "data"
BASS_RAW_DIR = os.path.join(BASE_DIR, "bass", "raw")
BASS_PROCESSED_DIR = os.path.join(BASE_DIR, "bass", "processed")

# Директории для сегментов
BASS_SEGMENTS_RAW_DIR = os.path.join(BASE_DIR, "bass_segments", "raw")
BASS_SEGMENTS_PROCESSED_DIR = os.path.join(BASE_DIR, "bass_segments", "processed")

os.makedirs(BASS_SEGMENTS_RAW_DIR, exist_ok=True)
os.makedirs(BASS_SEGMENTS_PROCESSED_DIR, exist_ok=True)

print("="*70)
print("Обучение УЛУЧШЕННОЙ U-Net модели обработки БАС-ГИТАРЫ")
print("="*70)

# Конфигурация
USE_COMPLEX = False  # True для ImprovedComplexUNet, False для ImprovedUNet
MODEL_TYPE = "improved_complex" if USE_COMPLEX else "improved_unet"

# Получаем список файлов и сопоставляем пары
def match_file_pairs(raw_dir, processed_dir):
    """
    Сопоставляет пары raw → processed файлов.
    Формат имён: XXX_raw.wav → XXX_processed.wav
    """
    raw_files = glob.glob(os.path.join(raw_dir, "*.wav"))
    processed_files = glob.glob(os.path.join(processed_dir, "*.wav"))
    
    pairs = []
    
    # Создаём словарь processed файлов по базовому имени
    processed_dict = {}
    for proc_path in processed_files:
        proc_name = Path(proc_path).stem
        # Убираем _processed чтобы получить базовое имя
        base_name = proc_name.replace('_processed', '')
        processed_dict[base_name] = proc_path
    
    for raw_path in raw_files:
        raw_name = Path(raw_path).stem
        # Убираем _raw чтобы получить базовое имя
        base_name = raw_name.replace('_raw', '')
        
        if base_name in processed_dict:
            pairs.append((raw_path, processed_dict[base_name]))
            print(f"  ✓ Найдена пара: {Path(raw_path).name} → {Path(processed_dict[base_name]).name}")
        else:
            print(f"  ⚠️ Не найдена пара для: {raw_name}")
    
    return pairs

print("\n" + "="*70)
print("Сопоставление пар raw → processed для БАС-ГИТАРЫ")
print("="*70)

file_pairs = match_file_pairs(BASS_RAW_DIR, BASS_PROCESSED_DIR)

if not file_pairs:
    print("\n⚠️ Не найдено пар файлов! Проверяем альтернативный метод сопоставления...")
    
    # Альтернативный метод: просто сопоставляем по порядку
    raw_files = sorted(glob.glob(os.path.join(BASS_RAW_DIR, "*.wav")))
    processed_files = sorted(glob.glob(os.path.join(BASS_PROCESSED_DIR, "*.wav")))
    
    if len(raw_files) == len(processed_files):
        file_pairs = list(zip(raw_files, processed_files))
        print(f"\n✓ Сопоставлено {len(file_pairs)} пар по порядку")
        for raw, proc in file_pairs:
            print(f"  {Path(raw).name} → {Path(proc).name}")
    else:
        print("\nERROR: Количество файлов не совпадает!")
        print(f"  Raw файлов: {len(raw_files)}")
        print(f"  Processed файлов: {len(processed_files)}")
        exit(1)

print("\n" + "="*70)
print(f"ВСЕГО НАЙДЕНО ПАР: {len(file_pairs)}")
print("="*70)

print("\n" + "="*70)
print("ЭТАП 1: Разбиение аудио на 15-секундные сегменты")
print("="*70)

SEGMENT_DURATION = 15.0
SAMPLE_RATE = 48000

raw_segments = glob.glob(os.path.join(BASS_SEGMENTS_RAW_DIR, "*.wav"))
processed_segments = glob.glob(os.path.join(BASS_SEGMENTS_PROCESSED_DIR, "*.wav"))

if len(raw_segments) > 0 and len(processed_segments) > 0:
    print("\n✓ Сегменты уже созданы ранее!")
    print(f"  Найдено сегментов сырых записей: {len(raw_segments)}")
    print(f"  Найдено сегментов обработанных записей: {len(processed_segments)}")
    
    # Проверяем консистентность
    if len(raw_segments) != len(processed_segments):
        print("\n⚠️ ВНИМАНИЕ: Количество сегментов не совпадает!")
        print(f"  Raw сегментов: {len(raw_segments)}")
        print(f"  Processed сегментов: {len(processed_segments)}")
        print("  Рекомендуется удалить старые сегменты и создать заново.")
else:
    print("\nСегменты не найдены, создаю новые...")
    print("\nОбработка сырых записей...")
    for raw_file, _ in file_pairs:
        split_and_save(raw_file, BASS_SEGMENTS_RAW_DIR, segment_duration=SEGMENT_DURATION, sample_rate=SAMPLE_RATE)

    print("\nОбработка обработанных записей...")
    for _, proc_file in file_pairs:
        split_and_save(proc_file, BASS_SEGMENTS_PROCESSED_DIR, segment_duration=SEGMENT_DURATION, sample_rate=SAMPLE_RATE)

# Финальная проверка консистентности и сопоставление пар
raw_segments = glob.glob(os.path.join(BASS_SEGMENTS_RAW_DIR, "*.wav"))
processed_segments = glob.glob(os.path.join(BASS_SEGMENTS_PROCESSED_DIR, "*.wav"))

print("\n" + "="*70)
print("ПРОВЕРКА КОНСИСТЕНТНОСТИ ДАННЫХ")
print("="*70)
print(f"  Raw сегментов: {len(raw_segments)}")
print(f"  Processed сегментов: {len(processed_segments)}")

# Сопоставляем сегменты по именам
def match_segments_by_name(raw_dir, processed_dir):
    """
    Сопоставляет сегменты по базовому имени.
    
    Новые форматы имён (после переименования):
    - Raw: segment_XXX_raw_NNNN.wav
    - Processed: segment_XXX_processed_NNNN.wav
    
    Ключ для сопоставления: XXX_NNNN
    """
    raw_files = glob.glob(os.path.join(raw_dir, "*.wav"))
    processed_files = glob.glob(os.path.join(processed_dir, "*.wav"))
    
    print(f"  Raw файлов: {len(raw_files)}")
    print(f"  Processed файлов: {len(processed_files)}")
    
    def extract_key(filepath):
        """
        Извлекает ключ для сопоставления из имени файла.
        segment_XXX_raw_NNNN.wav → XXX_NNNN
        segment_XXX_processed_NNNN.wav → XXX_NNNN
        """
        name = Path(filepath).stem
        # Убираем префикс 'segment_'
        if name.startswith('segment_'):
            name = name[8:]
        
        # Убираем _raw или _processed и получаем базовое имя + номер сегмента
        # Формат: XXX_raw_NNNN или XXX_processed_NNNN
        if '_raw_' in name:
            parts = name.split('_raw_')
            base = parts[0]
            seg_num = parts[1] if len(parts) > 1 else ''
            name = f"{base}_{seg_num}"
        elif '_processed_' in name:
            parts = name.split('_processed_')
            base = parts[0]
            seg_num = parts[1] if len(parts) > 1 else ''
            name = f"{base}_{seg_num}"
        
        return name
    
    # Создаём словарь processed файлов
    processed_dict = {}
    for proc_file in processed_files:
        key = extract_key(proc_file)
        processed_dict[key] = proc_file
    
    print(f"  Примеры ключей processed: {list(processed_dict.keys())[:3]}")
    
    matched_pairs = []
    unmatched_raw = []
    
    for raw_file in raw_files:
        key = extract_key(raw_file)
        if key in processed_dict:
            matched_pairs.append((raw_file, processed_dict[key]))
        else:
            unmatched_raw.append(raw_file)
    
    return matched_pairs, unmatched_raw

matched_pairs, unmatched_raw = match_segments_by_name(BASS_SEGMENTS_RAW_DIR, BASS_SEGMENTS_PROCESSED_DIR)

print(f"  Сопоставлено пар: {len(matched_pairs)}")

if unmatched_raw:
    print(f"  Не найдены пары для {len(unmatched_raw)} raw сегментов")
    # Удаляем несопоставленные raw сегменты
    for raw_file in unmatched_raw:
        os.remove(raw_file)
        print(f"    Удалён: {Path(raw_file).name}")

# Обновляем списки после удаления
raw_segments = glob.glob(os.path.join(BASS_SEGMENTS_RAW_DIR, "*.wav"))
processed_segments = glob.glob(os.path.join(BASS_SEGMENTS_PROCESSED_DIR, "*.wav"))

print(f"\n  Итоговое количество raw сегментов: {len(raw_segments)}")
print(f"  Итоговое количество processed сегментов: {len(processed_segments)}")

if len(raw_segments) != len(processed_segments):
    print("\n⚠️ ПРЕДУПРЕЖДЕНИЕ: Количество сегментов всё ещё не совпадает!")
    print("  Будут использованы только сопоставленные пары.")

print("\n" + "="*70)
print("ЭТАП 2: Подготовка датасета")
print("="*70)

# Создаём временные директории с сопоставленными файлами
MATCHED_RAW_DIR = BASS_SEGMENTS_RAW_DIR + "_matched"
MATCHED_PROCESSED_DIR = BASS_SEGMENTS_PROCESSED_DIR + "_matched"
os.makedirs(MATCHED_RAW_DIR, exist_ok=True)
os.makedirs(MATCHED_PROCESSED_DIR, exist_ok=True)

# Копируем только сопоставленные файлы

for raw_file, proc_file in matched_pairs:
    shutil.copy(raw_file, os.path.join(MATCHED_RAW_DIR, Path(raw_file).name))
    shutil.copy(proc_file, os.path.join(MATCHED_PROCESSED_DIR, Path(proc_file).name))

print(f"Скопировано {len(matched_pairs)} сопоставленных пар во временные директории")

dataset = AudioEffectDataset(MATCHED_RAW_DIR, MATCHED_PROCESSED_DIR, sample_rate=SAMPLE_RATE, use_complex=USE_COMPLEX)
print(f"\nОбщее количество сегментов: {len(dataset)}")

if len(dataset) == 0:
    print("ERROR: Датасет пуст! Проверьте пути к файлам.")
    exit(1)

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

# Комбинированная функция потерь (оригинальная - она работала!)
class CombinedLoss(nn.Module):
    """
    Комбинированная функция потерь.
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
        
        # Edge enhancement loss - градиенты по частоте
        grad_freq_out = output[:, :, 1:, :] - output[:, :, :-1, :]
        grad_freq_target = target[:, :, 1:, :] - target[:, :, :-1, :]
        edge_loss = nn.L1Loss()(grad_freq_out, grad_freq_target)
        
        return (
            self.l1_weight * l1_loss + 
            self.ssim_weight * ssim_loss +
            0.05 * edge_loss  # Уменьшенный вес для edge loss
        )

criterion = CombinedLoss(l1_weight=0.8, ssim_weight=0.2)

print(f"\nОптимизатор: Adam (lr={initial_lr})")
print("Scheduler: StepLR (step_size=15, gamma=0.5)")
print("Функция потерь: Combined (L1=0.8 + SSIM=0.2 + Edge=0.05)")

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
TARGET_LOSS = 0.015  # Реалистичный порог для баса (было 0.003 - нереалистично)

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
    print(f"\n💾 Восстановлена лучшая модель (loss={best_loss:.4f})")
    model.load_state_dict(best_model_state)

total_time = time.time() - start_time

# Сохранение весов модели
print("\n" + "="*70)
print("ЭТАП 5: Сохранение модели")
print("="*70)

model_type_str = "improved_complex" if USE_COMPLEX else "improved_unet"
model_path = f"model_weights_bass_{model_type_str}_02.pth"
torch.save(model.state_dict(), model_path)
print(f"\n✓ Модель сохранена: {model_path}")

# Выводим статистику
print("\n" + "="*70)
print("ИТОГОВАЯ СТАТИСТИКА")
print("="*70)

actual_epochs = len(epoch_losses)
print(f"Количество эпох: {actual_epochs}")
if early_stop:
    print("Ранняя остановка")
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
