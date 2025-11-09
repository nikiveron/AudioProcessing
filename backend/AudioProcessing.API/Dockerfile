# ===== 1. Build =====
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src

# NuGet folder FIX
ENV NUGET_PACKAGES=/root/.nuget/packages

# csproj
COPY backend/AudioProcessing.Domain/AudioProcessing.Domain.csproj backend/AudioProcessing.Domain/
COPY backend/AudioProcessing.Application/AudioProcessing.Application.csproj backend/AudioProcessing.Application/
COPY backend/AudioProcessing.Infrastructure/AudioProcessing.Infrastructure.csproj backend/AudioProcessing.Infrastructure/
COPY backend/AudioProcessing.API/AudioProcessing.API.csproj backend/AudioProcessing.API/

RUN dotnet restore backend/AudioProcessing.API/AudioProcessing.API.csproj

# source
COPY backend/AudioProcessing.Domain backend/AudioProcessing.Domain
COPY backend/AudioProcessing.Application backend/AudioProcessing.Application
COPY backend/AudioProcessing.Infrastructure backend/AudioProcessing.Infrastructure
COPY backend/AudioProcessing.API backend/AudioProcessing.API

RUN dotnet publish backend/AudioProcessing.API/AudioProcessing.API.csproj \
    -c Release -o /app/publish

# ===== 2. Runtime =====
FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS runtime
WORKDIR /app
COPY --from=build /app/publish .

ENV ASPNETCORE_URLS=http://+:8080
EXPOSE 8080

ENTRYPOINT ["dotnet", "AudioProcessing.API.dll"]
