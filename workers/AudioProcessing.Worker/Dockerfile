# ===== 1. Build stage =====
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src

# Копируем все csproj в правильной структуре
COPY backend/AudioProcessing.Domain/AudioProcessing.Domain.csproj backend/AudioProcessing.Domain/
COPY backend/AudioProcessing.Application/AudioProcessing.Application.csproj backend/AudioProcessing.Application/
COPY backend/AudioProcessing.Infrastructure/AudioProcessing.Infrastructure.csproj backend/AudioProcessing.Infrastructure/
COPY workers/AudioProcessing.Worker/AudioProcessing.Worker.csproj workers/AudioProcessing.Worker/

# Восстанавливаем зависимости worker
RUN dotnet restore workers/AudioProcessing.Worker/AudioProcessing.Worker.csproj

# Копируем исходники
COPY backend/AudioProcessing.Domain backend/AudioProcessing.Domain
COPY backend/AudioProcessing.Application backend/AudioProcessing.Application
COPY backend/AudioProcessing.Infrastructure backend/AudioProcessing.Infrastructure
COPY workers/AudioProcessing.Worker workers/AudioProcessing.Worker

# Публикация
RUN dotnet publish workers/AudioProcessing.Worker/AudioProcessing.Worker.csproj \
    -c Release -o /app/publish --no-restore

# ===== 2. Runtime =====
FROM mcr.microsoft.com/dotnet/runtime:9.0 AS runtime
WORKDIR /app

COPY --from=build /app/publish .

ENTRYPOINT ["dotnet", "AudioProcessing.Worker.dll"]
