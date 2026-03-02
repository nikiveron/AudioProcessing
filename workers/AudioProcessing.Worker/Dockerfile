# =========================
# 1️⃣ BUILD STAGE
# =========================
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src

# Копируем только нужные csproj
COPY backend/AudioProcessing.Domain/*.csproj backend/AudioProcessing.Domain/
COPY backend/AudioProcessing.Application/*.csproj backend/AudioProcessing.Application/
COPY backend/AudioProcessing.Infrastructure/*.csproj backend/AudioProcessing.Infrastructure/
COPY workers/AudioProcessing.Worker/*.csproj workers/AudioProcessing.Worker/

# Restore ТОЛЬКО worker
RUN dotnet restore workers/AudioProcessing.Worker/AudioProcessing.Worker.csproj

# Копируем исходники
COPY backend/ backend/
COPY workers/ workers/

# Publish
RUN dotnet publish workers/AudioProcessing.Worker/AudioProcessing.Worker.csproj \
    -c Release \
    -o /app/publish \
    /p:UseAppHost=false

# =========================
# 2️⃣ RUNTIME STAGE
# =========================
FROM mcr.microsoft.com/dotnet/runtime:9.0
WORKDIR /app

COPY --from=build /app/publish .

ENTRYPOINT ["dotnet", "AudioProcessing.Worker.dll"]
