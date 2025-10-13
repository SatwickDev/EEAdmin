FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    pkg-config \
    wget \
    unzip \
    poppler-utils \
    libpoppler-cpp-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libgthread-2.0-0 \
    libaio1 \
    && rm -rf /var/lib/apt/lists/*

# Install Oracle Instant Client
RUN wget -q https://download.oracle.com/otn_software/linux/instantclient/1923000/instantclient-basic-linux.x64-19.23.0.0.0dbru.zip \
    && unzip instantclient-basic-linux.x64-19.23.0.0.0dbru.zip -d /opt/ \
    && rm instantclient-basic-linux.x64-19.23.0.0.0dbru.zip \
    && echo "/opt/instantclient_19_23" > /etc/ld.so.conf.d/oracle-instantclient.conf \
    && ldconfig

# Set Oracle environment variables
ENV LD_LIBRARY_PATH=/opt/instantclient_19_23:$LD_LIBRARY_PATH
ENV ORACLE_CLIENT_LIB_DIR=/opt/instantclient_19_23

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/utils/output /app/chroma_db

# Expose port
EXPOSE 5000

# Run application
CMD ["python", "run.py"]