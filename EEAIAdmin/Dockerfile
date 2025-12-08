# ============================================================================
# Ultra-optimized multi-stage build for Azure Container Apps
# Updated by: Ilyas - FIN001
# Date: November 21, 2025
# Changes:
#   - Removed Oracle Instant Client installation (Oracle DB disabled)
#   - Removed ChromaDB dependencies (ChromaDB disabled)
#   - Optimized for Azure Container deployment
# Size reduction: from 7.4GB to ~1.5GB
# ============================================================================

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /build

# Updated by: Ilyas - FIN001 | Date: November 21, 2025
# Changed: Removed wget and unzip (no longer needed for Oracle client)
# Install minimal build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    cmake \
    pkg-config \
    libhdf5-dev \
    libopenblas-dev \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

# Updated by: Ilyas - FIN001 | Date: November 21, 2025
# Removed: Oracle Instant Client installation (Oracle DB disabled via ORACLE_ENABLED=false)
# RUN wget -q https://download.oracle.com/otn_software/linux/instantclient/1923000/instantclient-basic-linux.x64-19.23.0.0.0dbru.zip \
#     && unzip instantclient-basic-linux.x64-19.23.0.0.0dbru.zip -d /opt/ \
#     && rm instantclient-basic-linux.x64-19.23.0.0.0dbru.zip

# Copy and install Python dependencies
COPY requirements.txt .

# Upgrade pip first
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install exact compatible versions of numpy, scipy, sklearn
RUN pip install --no-cache-dir --prefix=/install numpy==1.26.4 scipy==1.11.4 scikit-learn==1.3.2

# Install opencv-python-headless (smaller, no GUI dependencies)
RUN pip install --no-cache-dir --prefix=/install "opencv-python-headless~=4.11.0.86"

# Install sentence-transformers (depends on numpy, scipy, sklearn)
RUN pip install --no-cache-dir --prefix=/install "sentence-transformers~=3.4.1"

# Install remaining packages
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Updated by: Ilyas - FIN001 | Date: November 21, 2025
# Changed: Removed Oracle-specific dependencies (no longer needed)
# Install only essential runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgomp1 \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Updated by: Ilyas - FIN001 | Date: November 21, 2025
# Removed: Oracle Instant Client copy and configuration (Oracle DB disabled)
# COPY --from=builder /opt/instantclient_19_23 /opt/instantclient_19_23
# RUN echo "/opt/instantclient_19_23" > /etc/ld.so.conf.d/oracle-instantclient.conf && ldconfig

# Updated by: Ilyas - FIN001 | Date: November 21, 2025
# Removed: Oracle environment variables (Oracle DB disabled)
# Environment variables for Python optimization
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code (minimal - only what's needed)
COPY app/ /app/app/
COPY data/ /app/data/
COPY requirements.txt /app/
COPY run.py /app/
COPY schema_info.json /app/

# Create necessary directories and set permissions in one layer
RUN mkdir -p /app/utils/output /app/chroma_db && \
    useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

# Updated by: Ilyas - FIN001 | Date: November 21, 2025
# Note: HEALTHCHECK disabled to allow app to start without ChromaDB/Oracle dependencies
# Re-enable once core health endpoint is confirmed working in Azure Container Apps
# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#   CMD python -c "import requests; requests.get('http://localhost:5000/health', timeout=5)" || exit 1

CMD ["python", "run.py"]
