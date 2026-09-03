# Gunakan OS sistem Python yang ringan
FROM python:3.11-slim

# Buat folder kerja di dalam mesin virtual
WORKDIR /app

# Salin file daftar pustaka ke mesin virtual
COPY requirements.txt .

# Install semua pustaka tanpa menyimpan cache agar memori tetap lega
RUN pip install --no-cache-dir -r requirements.txt

# Salin seluruh file kode kamu (termasuk app.py)
COPY . .

# Buka port 8080 (wajib untuk Google Cloud Run)
EXPOSE 8080

# Jalankan Streamlit saat mesin dihidupkan
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
