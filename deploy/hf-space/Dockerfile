FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir \
    transformers>=4.49 \
    accelerate>=1.0 \
    fastapi \
    uvicorn \
    huggingface_hub

COPY app.py .

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
