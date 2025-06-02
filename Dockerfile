FROM python:3.13.3-bullseye

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure Piper binaries are executable for both amd64 and arm64
RUN chmod +x server-assets/piper/linux-amd64/piper || true \
    && chmod +x server-assets/piper/linux-arm64/piper || true

EXPOSE 8084

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8084"]
