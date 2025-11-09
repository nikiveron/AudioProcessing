FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости

RUN pip install --no-cache-dir -r requirements.txt

# Копируем код ML-сервиса
COPY . .

# Экспонируем gRPC порт
EXPOSE 50051

# Точка входа: запускаем gRPC сервер
CMD ["python", "main.py"]