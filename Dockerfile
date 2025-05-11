FROM python:3.11-slim

# Sistem bağımlılıklarını yükle (OpenCV ve bazı GUI bağımlılıkları için gerekli)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Çalışma dizini
WORKDIR /app

# Gerekli Python bağımlılıklarını kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# Uygulama başlatma komutu
CMD ["python", "main.py"]
