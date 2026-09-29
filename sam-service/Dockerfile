FROM nvidia/cuda:12.8.0-runtime-ubuntu24.04

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/models/huggingface

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3.12 python3.12-venv python3-pip git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN python3.12 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir fastapi uvicorn[standard] httpx pillow huggingface-hub einops ninja pycocotools psutil \
    && pip install --no-cache-dir torch==2.10.0 torchvision --index-url https://download.pytorch.org/whl/cu128

# Install current SAM 3 code. Checkpoints are gated and should be downloaded at runtime
# with HF_TOKEN/s env after access to facebook/sam3.1 has been granted.
RUN git clone https://github.com/facebookresearch/sam3.git /opt/sam3 \
    && pip install --no-cache-dir -e /opt/sam3

COPY app.py .

EXPOSE 8100

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8100"]
